# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
from typing import Union
from constants import *
from base64 import b64encode
import time
import os


class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.
    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """

    def __init__(self, socket, directory):
        # Inicializar atributos de Connection
        self.socket = socket
        self.directory = directory

    def handle(self) -> None:
        """
        Atiende eventos de la conexión hasta que termina.
        """

        try:
            while True:
                request = self.read_till_EOL(60, 60)
                print(f"Request: {request} " + f"From: {self.socket.getpeername()}")
                request = request.split()
                if not request:
                    break
                elif not self.validate_input(request):
                    break
                elif request[0].lower() == "quit":
                    if len(request) != 1:
                        self.print_to_client(msg_to_client[INVALID_ARGUMENTS])
                    else:
                        self.quit()
                        break
                elif request[0].lower() == "get_slice":
                    is_valid = self.get_slice(request)
                    if not is_valid:
                        break
                elif request[0].lower() == "get_metadata":
                    self.get_metadata(request)
                elif request[0].lower() == "get_file_listing":
                    self.get_file_listing()
                else:
                    self.print_to_client(msg_to_client[INVALID_COMMAND])
        except Exception:
            self.print_to_client(msg_to_client[INTERNAL_ERROR])
        finally:
            self.socket.close()

    def print_to_client(self, msg: str) -> None:
        """
        Envia al cliente un mensaje con codificacion ascii
        ademas concatena \\r\\n al final de la linea para
        indicar el final de la linea

        Args:
            msg (str): mensaje a ser enviado
        """
        msg += EOL
        msg = msg.encode("ascii")
        self.socket.send(msg)

    def read_till_EOL(self,
                      single_cmd_timeout: int = None,
                      general_timeout: int = None
                      ) -> Union[str, None]:
        """
        Reads and returns data from client input stream till EOL
        is found or timeout time is excedeed
        (both from socket timeout or reading multiple streams timeout)

        Args:
            single_cmd_timeout (int, optional): time in seconds for the recv
            command to be reading data. Defaults to None
            timeout (int, optional): time in seconds for the function to be
            reading data. Defaults to None.

        Returns:
            str or None: readed data decoded using ascii or
            None in case of empty
        """

        s = self.socket
        data = ''
        s.settimeout(single_cmd_timeout)
        if general_timeout is not None:
            t1 = time.process_time()
        else:
            general_timeout = 0
        try:
            while EOL not in data and general_timeout > 0:
                data += s.recv(4096).decode("ascii")
                if general_timeout is not None:
                    t2 = time.process_time()
                    general_timeout -= t2 - t1
                    t1 = t2
            if EOL in data:
                data = (data.split(EOL, 1)[0]).strip()
                if '\n' in data:
                    self.print_to_client(msg_to_client[BAD_EOL])
                    return None
                return data
            else:
                self.print_to_client(msg_to_client[BAD_REQUEST])
                return None
        except TimeoutError:
            self.print_to_client(msg_to_client[TIMEOUT])
            return None
        except UnicodeDecodeError:
            self.print_to_client(msg_to_client[BAD_REQUEST])
            return None
        except KeyboardInterrupt:
            return None

    def validate_input(self, input: str) -> bool:
        """
        Validates input data given the VALID_CHARS constant
        Sends BAD_REQUEST code to client when there is
        an invalid input
        Args:
            input (str): input string

        Returns:
            bool: valid or not
        """
        input = "".join(input)
        response = True
        for char in input:
            response = response and (char in VALID_CHARS)
        if not response:
            self.print_to_client(msg_to_client[BAD_REQUEST])
        return response

    def quit(self):
        """
        Sends OK code to client and closes the connection socket
        """

        self.print_to_client(msg_to_client[CODE_OK])
        self.socket.close()

    def get_metadata(self, request: list[str]) -> None:
        """
        Sends the size in bytes of the requested file to the client.

        Sends an ERROR: FILE NOT FOUND message if the file does not exist.
        Sends an ERROR: INVALID ARGUMENTS message
            if the request format is incorrect.

        Args:
            request (list[str]): input command split into arguments

        Example:
            get_metadata Branca.txt
                0 OK
                29
        """
        if len(request) != 2:
            self.print_to_client(msg_to_client[INVALID_ARGUMENTS])
        elif len(request[1]) > DEFAUL_MAX_PATH:
                self.print_to_client(msg_to_client[FILE_NOT_FOUND])
        else:
            try:
                filepath = os.path.join(self.directory + '/', request[1])
                size = os.path.getsize(filepath)
                self.print_to_client(msg_to_client[CODE_OK])
                self.print_to_client(f"{size}")
            except FileNotFoundError:
                self.print_to_client(msg_to_client[FILE_NOT_FOUND])

    def get_slice(self, request: list[str]) -> bool:
        """
        Sends the requested file fragment encoded in Base64 to the client.
            Sends an ERROR: FILE NOT FOUND message if the file does not exist.
            Sends an ERROR: INVALID ARGUMENTS message
                if occurs any error in the arguments

        Args:
            request (list[str]): input string divide in arguments

        Returns:
            True if request not malicious
            False if request malicious (offset + size > filesize)

        Example:
        get_slice Birra.txt 5 20
            0 OK
            Y2Fsb3IgcXVlIGhhY2UgaG95LCA=
        """
        if len(request) != 4:
            self.print_to_client(msg_to_client[INVALID_ARGUMENTS])
        else:
            file = request[1]
            try:
                offset = int(request[2])
                size = int(request[3])

                if offset < 0 or size < 0:
                    self.print_to_client(msg_to_client[INVALID_ARGUMENTS])

                filesize = os.path.getsize(self.directory + '/' + file)
                if offset + size > filesize:
                            self.print_to_client(msg_to_client[BAD_REQUEST])
                            self.socket.close()
                            return False

                with open(self.directory + '/' + file, "rb") as f:
                    f.seek(offset)

                    response = f.read(size)
                    response = b64encode(response)
                    response += bytes(EOL, 'utf-8')

                    self.print_to_client(msg_to_client[CODE_OK])

                    self.socket.send(response)

                    f.close()
            except FileNotFoundError:
                self.print_to_client(msg_to_client[FILE_NOT_FOUND])
            except ValueError:
                self.print_to_client(msg_to_client[INVALID_ARGUMENTS])
        return True

    def get_file_listing(self) -> None:
        """
        Gets a list of all files in the directory.
            This function takes no arguments.
        """
        try:
            flist = os.listdir(self.directory)
            code_message = msg_to_client[CODE_OK] + EOL
            if not flist:
                self.print_to_client(code_message)
            else:
                file_list = EOL.join(flist) + EOL
                self.print_to_client(code_message + file_list)
        except Exception:
            self.print_to_client(msg_to_client[INTERNAL_ERROR])
            self.print_to_client(f"No existe la carpeta")
