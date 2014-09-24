#!/usr/bin/python

from twisted.internet.protocol import Protocol
from twisted.internet.protocol import ClientFactory
from twisted.internet.endpoints import TCP4ClientEndpoint


class Echo(Protocol):
    def dataReceived(self, data):
        self.transport.write(data)


class EchoClientFactory(ClientFactory):
    def buildProtocol(self, addr):
        return Echo()


def main():
    from twisted.internet import reactor
    point = TCP4ClientEndpoint(reactor, "localhost", 3578)
    point.connect(EchoClientFactory())
    reactor.run()
    

if __name__ == "__main__":
    main()
