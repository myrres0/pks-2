import binascii
import math
import os.path
import socket
import struct
import sys
import threading
import time

# for keep alive
thread = None
thread_flag = False


def keep_alive(client_sock, server_address):
    global thread_flag
    global thread
    try:
        while True:
            if not thread_flag:
                return
            # sending keep alive message to server
            client_sock.sendto(str.encode("2"), server_address)
            # if no response from server for 30 sec, close connection
            client_sock.settimeout(30)
            # waiting for response from server
            data, address = client_sock.recvfrom(1472)
            if data.decode() == "2":
                time.sleep(5)
                continue
    except socket.timeout:
        print("no response from server")
        time.sleep(1)
        client_sock.close()
        menu_client()
        return
    except Exception as error:
        print(error)
        time.sleep(1)
        client_sock.close()
        #menu_client()
        exit()

    
def start_thread(client_sock, server_address):
    global thread_flag
    global thread
    thread = threading.Thread(target=keep_alive, args=(client_sock, server_address))
    thread_flag = True
    thread.start()


def create_client(server_ip, port):
    exit_choice = input("Type 1 to exit, anything to continue: ")
    if exit_choice == "1":
        return
    while True:
        try:
            # creting socket for udp for client
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_address = (server_ip, int(port))
            client_ip = socket.gethostbyname(socket.gethostname())
            client_sock.sendto(str.encode("1"), server_address)  # initial message
            # waiting for response from server
            print("trying to connect to server")
            client_sock.settimeout(5)
            data, address = client_sock.recvfrom(1472)
            data = data.decode()
            if data == "1":  # if server is alive
                print("Connected to server")
                client(client_sock, server_address, port)
        except (socket.timeout, socket.gaierror) as error:
            print(error)
            print("cannot connect to server, try again")
            exit_choice = input("Type 1 to exit, anything to continue: ")
            if exit_choice == "1":
                return
            server_ip = input("Input ip of the server: ")
            port = input("Input port: ")
            time.sleep(1)
            continue  # trying to connect again



def create_server(port):
    # creating socket for udp for server
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_ip = socket.gethostbyname(socket.gethostname())
    print("Server ip: ", server_ip)
    server_sock.bind(("", int(port)))  # creating server
    init_server(server_sock, port)


def init_server(server_sock, port):
    # send respond for the initial message
    try:
        server_sock.settimeout(30)
        while True:
            data, address = server_sock.recvfrom(1472)
            if data.decode() == "1":
                server_sock.sendto(str.encode("1"), address)
                print("Connected to client with address: ", address)  # connection is established
                server(server_sock, port)
                break
    except socket.timeout:
        print("no response from client")
        time.sleep(1)
        server_sock.close()
        menu_server()
        return

    return address

def menu_server():
    port = input("Input port: ")
    create_server(port)

def menu_client():
    server_ip = input("Input ip of the server: ")
    port = input("Input port: ")
    time.sleep(2)
    create_client(server_ip, port)


def client(client_sock, server_address, port):
    global thread_flag
    global thread
    start_thread(client_sock, server_address)
    while True:
        print("1 - exit")
        print("2 - switch client and server")
        print("3 - send message to server")
        choice = input("Your choice: ")
        if choice == "1":
            thread_flag = False
            if thread is not None:
                thread.join()
                thread = None
            client_sock.sendto(str.encode("6"), server_address)  # finish communication
            data, address = client_sock.recvfrom(1472)
            data = data.decode()
            if data == "6":
                time.sleep(1)
                print("Disconnected from server")
                client_sock.close()
                menu_client()
            time.sleep(1)

        if choice == "2":
            thread_flag = False
            if thread is not None:
                thread.join()
                thread = None
            client_sock.sendto(str.encode("3"), server_address)
            data, address = client_sock.recvfrom(1472)
            data = data.decode()
            if data == "3":
                time.sleep(1)
                print("Disconnected from server")
                client_sock.close()
                time.sleep(3)
                create_server(port)
            return
        if choice == "3":
            send_to_server(client_sock, server_address)
            data, address = client_sock.recvfrom(1472)
            data = data.decode()
            if data == "3":
                client_sock.sendto(str.encode("3"), server_address)
                time.sleep(1)
                print("Disconnected from server")
                client_sock.close()
                time.sleep(3)
                print("Switching to server")
                create_server(port)
            start_thread(client_sock, server_address)
            continue




def send_to_server(client_sock, server_address):
    global number_of_fragments
    global thread
    global thread_flag
    type_file = 0  # 1 - message, 2 - file
    print("Write 1 if you want to send message to server")
    print("Write 2 if you want to send file to server")
    choice = (input("Your choice: "))
    if choice != "1" and choice != "2":
        print("Wrong choice")
        return
    choice = int(choice)
    fragment_size = int(input("Input fragment size: "))
    while fragment_size > 1460 or fragment_size < 1:
        print("Wrong fragment size")
        fragment_size = int(input("Input fragment size: "))

    # if client sending a message
    if choice == 1:
        message = input("Input your message: ")
        # message to bytes
        message = str.encode(message)
        # count number of fragments to send
        number_of_fragments = math.ceil(len(message) / fragment_size)
        type_file = 1

    # if client sending a file
    if choice == 2:
        file_name = input("Input file name: ")
        file_path = os.path.abspath(file_name)
        try:
            file = open(file_path, "rb")
            print("Path: ", file_path)
        except FileNotFoundError:
            print("File not found")
            return
        thread_flag = False
        if thread is not None:
            thread.join()
            thread = None
        header = struct.pack("c", str.encode("8"))
        client_sock.sendto(header + str.encode(file_name), server_address)
        data, address = client_sock.recvfrom(1472)
        data = data.decode()
        if data != "5":
            print("Wrong response from server")
            return
        # size of file in bytes
        file_size = os.path.getsize(file_name)
        number_of_fragments = math.ceil(file_size / fragment_size)
        message = file.read()
        file.close()
        type_file = 2

    thread_flag = False
    if thread is not None:
        thread.join()
        thread = None
    packet_order = 0
    # sending number of fragments to server
    mistake_packets = make_mistake_packets(number_of_fragments)
    try:
        while message:
            client_sock.settimeout(30)
            if len(message) == 0:
                break
            part_message = message[:fragment_size]
            if type_file == 1:
                header = struct.pack("cHHHH", str.encode("4"), fragment_size, len(part_message), number_of_fragments,
                                     packet_order)
            else:
                header = struct.pack("cHHHH", str.encode("5"), fragment_size, len(part_message), number_of_fragments,
                                     packet_order)
            crc = binascii.crc_hqx(header + part_message, 0)
            if packet_order in mistake_packets:
                print("Mistake in packet: " + str(packet_order))
                crc += 1
            header = header + struct.pack("H", crc)
            client_sock.sendto(header + part_message, server_address)
            data, address = client_sock.recvfrom(1472)
            if data.decode() != "5":
                print("Fragment bol chybny, posielam znova")
                mistake_packets.remove(packet_order)
            else:
                packet_order += 1
                print("sended fragment number: ", packet_order, " of ", number_of_fragments)
                message = message[fragment_size:]
    except socket.timeout:
        print("no response from server")
        time.sleep(1)
        client_sock.close()
        menu_client()



def make_mistake_packets(number_of_packets):
    mistake_packets = []
    for i in range(number_of_packets):
        if i % int(number_of_packets) == 0:
            mistake_packets.append(i)
        if i % int(number_of_packets) == 2:
            mistake_packets.append(i)
        if i % int(number_of_packets) == 5:
            mistake_packets.append(i)
    return mistake_packets


def receive_server(server_sock, port):
    file_name = ""
    result_list = []
    message_type = 4  # 4 - message, 5 - file
    size_sum = 0
    while True:
        data, client_address = server_sock.recvfrom(1472)
        typ = data[:1]  # first byte is type
        if str(typ.decode()) == "2":
            print("keep alive message")
            server_sock.sendto(str.encode("2"), client_address)
            continue
        elif str(typ.decode()) == "3":
            server_sock.sendto(str.encode("3"), client_address)
            server_sock.close()
            time.sleep(2)
            print("Switching to client")
            time.sleep(3)
            create_client(client_address[0], port)
            return
        elif str(typ.decode()) == "4":  # we received message with data
            unpacked_data = struct.unpack("cHHHHH", data[:12])
            type_header, fragment_size, part_message_size, number_of_fragments, packet_order, crc = unpacked_data
            data_for_check = data[:10]+data[12:]
            check_crc = binascii.crc_hqx(data_for_check, 0)
            if check_crc == crc:
                size_sum += part_message_size
                server_sock.sendto(str.encode("5"), client_address)
                result_list.append([packet_order, data[12:].decode()])
                if len(result_list) == number_of_fragments:
                    break
            else:
                server_sock.sendto(str.encode("7"), client_address)  #stop and wait
                print("received " + str(packet_order) + " fragment with wrong crc")
                continue
        elif str(typ.decode()) == "8":
            message_type = 5
            file_name = data[1:].decode()
            server_sock.sendto(str.encode("5"), client_address)
            continue
        elif str(typ.decode()) == "5":  # we received message with data
            message_type = 5
            unpacked_data = struct.unpack("cHHHHH", data[:12])
            type_header, fragment_size, part_message_size, number_of_fragments, packet_order, crc = unpacked_data
            data_for_check = data[:10] + data[12:]
            check_crc = binascii.crc_hqx(data_for_check, 0)
            if check_crc == crc:
                size_sum += part_message_size
                server_sock.sendto(str.encode("5"), client_address)
                result_list.append([packet_order, data[12:]])
                if len(result_list) == number_of_fragments:
                    break
            else:
                print("received " + str(packet_order) + " fragment with wrong crc")
                server_sock.sendto(str.encode("7"), client_address)
                continue
        elif str(typ.decode()) == "6":
            print("client disconnected")
            server_sock.sendto(str.encode("6"), client_address)
            return -1
        else:
            print("wrong type")
            continue
    result_list.sort(key=lambda x: x[0])
    print("Number of fragments: ", number_of_fragments)
    print("Size of fragment: ", fragment_size)
    print("Size of message: ", size_sum)
    if message_type == 4:
        result_string = "".join(result_list[i][1] for i in range(len(result_list)))
        print("Received message: ", result_string)
    else:
        while True:
            file_path = input("Write path to save file: ")
            if not os.path.exists(file_path):
                print("Path does not exist")
                continue
            break
        file_path = file_path + "\\" + file_name
        with open(file_path, "wb") as file:
            for fragment in result_list:
                file.write(fragment[1])
            file.close()
        print("Received file: ", file_name)
        print("path: ", file_path)
    switch_user = input("Do you want to switch user? (y/n): ")
    if switch_user == "y":
        server_sock.sendto(str.encode("3"), client_address)
        data, client_address = server_sock.recvfrom(1472)
        if data.decode() == "3":
            print("Disconnectting from client")
            server_sock.close()
            print("Closed server")
            time.sleep(6)
            print("Switching to client")
            create_client(client_address[0], port)
    elif switch_user == "n":
        server_sock.sendto(str.encode(str("9")), client_address)


def server(server_sock, port):
    while True:
        print("1 - exit")
        print("Anything to continue")
        choice = input("Your choice: ")
        if choice == "1":
            time.sleep(1)
            server_sock.close()
            return
        print("server is waiting for message from client")
        if receive_server(server_sock, port) == -1:
            init_server(server_sock, port)
            return


def main():
    print("Choose client or server")
    print("1. Client")
    print("2. Server")
    choice = input("Your choice: ")
    if choice == "1":
        server_ip = input("Input ip of the server: ")
        port = input("Input port: ")
        create_client(server_ip, port)
    elif choice == "2":
        port = input("Input port: ")
        create_server(port)
    else:
        print("Wrong choice")
        return


if __name__ == "__main__":
    main()
