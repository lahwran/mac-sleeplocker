# translated pretty much line-by-line from ceylon
# 'cause I'm too lazy to reimplement python style when I have working code
# (note that a lot of stuff here is bad form in ceylon too >.>)

import datetime
import os
import sys

from twisted.internet.utils import getProcessOutput
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.protocol import Protocol, Factory
from twisted.python import log

log.startLogging(sys.stdout)
mydir = os.path.dirname(os.path.abspath(__file__))
log.startLogging(open(os.path.join(mydir, 'log'), 'a'), setStdout=False)

sleepdisplay = os.path.expanduser("~/bin/sleepdisplay")

def instantiate(cls):
    return cls()


class Day(object):
    @property
    def next_change(self):
        n = datetime.datetime.now().time()
        if n >= self.night.start:
            return datetime.time(0, 10)
        elif n >= self.evening.start:
            return self.night.start
        elif n >= self.day.start:
            return self.evening.start
        else:
            return self.day.start

    @property
    def current(self):
        n = datetime.datetime.now().time()
        if n >= self.night.start:
            return self.night
        elif n >= self.evening.start:
            return self.evening
        elif n >= self.day.start:
            return self.day
        else:
            return self.morning

@inlineCallbacks
def check_admin(reactor):
    output = yield getProcessOutput("dsmemberutil",
        args=["checkmembership", "-U", "lahwran", "-G", "admin"],
        reactor=reactor)
    returnValue("is a member" in output)

@inlineCallbacks
def grant_admin(reactor):
    print "grant admin"
    yield getProcessOutput("sudo",
            ["dseditgroup", "-o", "edit", "-a", "lahwran", "-t", "user", "admin"],
            reactor=reactor, env=os.environ)

@inlineCallbacks
def revoke_admin(reactor):
    print "revoke admin"
    yield getProcessOutput("sudo",
            ["dseditgroup", "-o", "edit", "-d", "lahwran", "-t", "user", "admin"],
            reactor=reactor, env=os.environ)

class Phase(object):
    def __init__(self, start, allow_admin, lock_screen, allow_begin_inhibit):
        self.start = start
        self.allow_admin = allow_admin
        self.lock_screen = lock_screen
        self.allow_begin_inhibit = allow_begin_inhibit

    @inlineCallbacks
    def update_admin(self, reactor):
        print "a"
        has_admin = yield check_admin(reactor)
        print "has admin:", has_admin
        if has_admin == self.allow_admin:
            return
        elif self.allow_admin:
            yield grant_admin(reactor)
        else:
            yield revoke_admin(reactor)
        print "b"

    def __repr__(self):
        return "<Phase %r %s%s%s>" % (
                self.start,
                "admin" if self.allow_admin else "no admin",
                " lock" if self.lock_screen else "",
                " begin inhibit" if self.allow_begin_inhibit else "")


class Inhibitor(Protocol):
    def __init__(self, reactor, phases):
        self.reactor = reactor
        self.phases = phases
        self.phase = phases.current
        self.disconnecter = None
        self.sender = None

    def connectionMade(self):
        if not self.phase.allow_begin_inhibit:
            self.transport.loseConnection()
        self.phases.inhibitors.append(self)
        c = self.phases.current
        print "Inhibiting. current phase:", c
        self.send_stuff()

    def send_stuff(self):
        self.transport.write("x" * 20)
        if self.disconnecter is not None and self.disconnecter.active():
            self.disconnecter.cancel()
        self.disconnecter = self.reactor.callLater(10, self.disconnect)

    def connectionLost(self, reason):
        print "Lost connection with inhibitor. de-inhibiting in 3 seconds."
        if self.disconnecter is not None and self.disconnecter.active():
            self.disconnecter.cancel()
        if self.sender is not None and self.sender.active():
            self.sender.cancel()
        self.disconnecter = self.reactor.callLater(3, self.finish)

    def finish(self):
        if self in self.phases.inhibitors:
            self.phases.inhibitors.remove(self)
        c = self.phases.current
        print "De-inhibiting.", c
        self.phases.current.update_admin(self.reactor)
        pc = self.phases.alarmthingy.waiting_phase_change
        if pc is not None and pc.active():
            pc.cancel()
        self.phases.alarmthingy.set_alarms()

    def disconnect(self):
        self.transport.loseConnection()

    def dataReceived(self, data):
        if self.disconnecter is not None and self.disconnecter.active():
            self.disconnecter.cancel()
        if self.sender is not None and self.sender.active():
            return
        self.sender = self.reactor.callLater(5, self.send_stuff)



class Phases(Factory):
    # this class is crap

    @instantiate
    class weekday(Day):
        morning = Phase(
            start=datetime.time(0, 0),
            allow_admin=False,
            lock_screen=True,
            allow_begin_inhibit=False
        )
        day = Phase(
            start=datetime.time(7, 00),
            allow_admin=True,
            lock_screen=False,
            allow_begin_inhibit=True
        )
        evening = Phase(
            start=datetime.time(12 + 6, 30),
            allow_admin=False,
            lock_screen=False,
            allow_begin_inhibit=False,
        )
        night = Phase(
            start=datetime.time(12 + 9, 00),
            allow_admin=False,
            lock_screen=True,
            allow_begin_inhibit=False,
        )

    @instantiate
    class weekend(Day):
        morning = Phase(
            start=datetime.time(0, 0),
            allow_admin=False,
            lock_screen=True,
            allow_begin_inhibit=False
        )
        day = Phase(
            start=datetime.time(8, 00),
            allow_admin=True,
            lock_screen=False,
            allow_begin_inhibit=True
        )
        evening = Phase(
            start=datetime.time(12 + 7, 30),
            allow_admin=False,
            lock_screen=False,
            allow_begin_inhibit=True,
        )
        night = Phase(
            start=datetime.time(12 + 9, 00),
            allow_admin=False,
            lock_screen=True,
            allow_begin_inhibit=False,
        )

    def __init__(self, reactor):
        self.reactor = reactor
        self.inhibitors = []

    def buildProtocol(self, addr):
        return Inhibitor(self.reactor, self)

    @property
    def today(self):
        if datetime.datetime.now().weekday() in [5, 6]:
            return self.weekend
        return self.weekday

    @property
    def next_change(self):
        return self.today.next_change

    @property
    def current(self):
        if self.inhibitors:
            print "INHIBITED TO:", self.inhibitors[0].phase
            return self.inhibitors[0].phase
        return self.today.current


def next_instance_of_time(time):
    now = datetime.datetime.now()
    today = now.date()
    dt = datetime.datetime.combine(today, time)
    if dt < now:
        dt += datetime.timedelta(days=1)
    return dt


@inlineCallbacks
def lock():
    yield getProcessOutput(sleepdisplay, [sleepdisplay])


class AlarmThingy(object):
    lock_interval = 3
    reactor_keepalive = 10

    # has state - waiting alarms - should it be a class though?

    def __init__(self, phases, reactor):
        self.reactor = reactor
        self.phases = phases
        self.waiting_poll = None
        self.waiting_phase_change = None

    @inlineCallbacks
    def poll(self):
        print "poll"
        if self.phases.current.lock_screen:
            yield lock()
        self.set_alarms()

    @inlineCallbacks
    def phase_change(self):
        print "phase_change"
        yield self.phases.current.update_admin(self.reactor)
        print self.phases.current
        self.set_alarms()

    def set_alarms(self):
        currentphase = self.phases.current

        if self.waiting_poll and self.waiting_poll.active():
            self.waiting_poll.cancel()

        if currentphase.lock_screen:
            print "lock"
            self.waiting_poll = self.reactor.callLater(
                    self.lock_interval, self.poll)
        else:
            print "keepalive"
            self.waiting_poll = self.reactor.callLater(
                    self.reactor_keepalive, self.set_alarms)

        next_change = next_instance_of_time(self.phases.next_change)
        if self.waiting_phase_change and self.waiting_phase_change.active():
            return
        delta = (next_change - datetime.datetime.now()).total_seconds()
        assert delta > 0, "Oops: %r %r %r" % (next_change, self.phases.current, delta)
        print "next change:", next_change
        self.waiting_phase_change = self.reactor.callLater(delta + 5,
                self.phase_change)


def main():
    from twisted.internet import reactor

    phases = Phases(reactor)
    endpoint = TCP4ServerEndpoint(reactor, 3578, interface="127.0.0.1")
    endpoint.listen(phases)

    alarmthingy = AlarmThingy(phases, reactor)
    phases.alarmthingy = alarmthingy
    alarmthingy.set_alarms()
    phases.current.update_admin(reactor)
    print "run reactor"
    reactor.run()

print "starting"
main()
