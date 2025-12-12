#!/usr/bin/env python
# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Revisión 2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: server.py 656 2013-03-18 23:49:11Z bc $

import optparse
import socket
from connection import Connection
import connection
from constants import *
import threading


class Server(object):
    """
    El servidor, que crea y atiende el socket en la dirección y puerto
    especificados donde se reciben nuevas conexiones de clientes.
    """

    def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT,
                 directory=DEFAULT_DIR):
        print("Serving %s on %s:%s." % (directory, addr, port))
        # Crear socket del servidor, configurarlo, asignarlo
        # a una dirección y puerto, etc.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((addr, port))
        self.server_socket = s
        self.addr = addr
        self.directory = directory

    def handle_connection(self, clien_conn, dir):
        conn = Connection(clien_conn, dir)
        conn.handle()

    def serve(self):
        """
        Loop principal del servidor. Se acepta una conexión a la vez
        y se espera a que concluya antes de seguir.
        """

        all_threads = []
        s = self.server_socket
        try:
            while True:
                s.listen(1)
                client_conn, addr = s.accept()
                print(f'Connected by {addr}')
                t = threading.Thread(target=self.handle_connection, args=(client_conn, self.directory), daemon=True)
                t.start()
                all_threads.append(t)

        except OSError as msg:
            print(msg)
            print("\nclosing server safely \n")
            s.close()
        except KeyboardInterrupt:
            print("CTRL+C DETECTED")
            s.close()
        finally:
            if s:
                s.close()
            for t in all_threads:
                t.join(timeout=1)


def main():
    """Parsea los argumentos y lanza el server"""

    parser = optparse.OptionParser()
    parser.add_option(
        "-p", "--port",
        help="Número de puerto TCP donde escuchar", default=DEFAULT_PORT)
    parser.add_option(
        "-a", "--address",
        help="Dirección donde escuchar", default=DEFAULT_ADDR)
    parser.add_option(
        "-d", "--datadir",
        help="Directorio compartido", default=DEFAULT_DIR)

    options, args = parser.parse_args()
    if len(args) > 0:
        parser.print_help()
        sys.exit(1)
    try:
        port = int(options.port)
    except ValueError:
        sys.stderr.write(
            "Numero de puerto invalido: %s\n" % repr(options.port))
        parser.print_help()
        sys.exit(1)

    server = Server(options.address, port, options.datadir)
    server.serve()


if __name__ == '__main__':
    main()
