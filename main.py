from __future__ import annotations
import virtualbox, json, pprint, configparser, time, psutil, sys, subprocess, os
from pypresence import Presence

p = subprocess.Popen("C:\Program Files\Oracle\VirtualBox\VirtualBox.exe")

pid = p.pid

class RichPresence:
    def __init__(self):

        # Initialize the VirtualBox instance, config, and assets.
        self.virtualbox = virtualbox.VirtualBox()
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")
        self.assets = json.load(open("assets.json", "r"))

        # Initialize the Rich Presence.
        client_id = self.config["Rich Presence"]["client_id"]
        self.RPC = Presence(client_id)
        self.RPC.connect()

        # Initialize format dictionary.
        self.format_dict = {"start": time.time()}

        while True:

            # Check if VirtualBox is running, and that the current OS is Windows.
            # [TODO] Add support for other operating systems.
            if (
                "VirtualBox.exe" in (p.name() for p in psutil.process_iter())
                or "VirtualBoxVM.exe" in (p.name() for p in psutil.process_iter())
            ):

                # Generate the list of machines.
                self.machine_list = self.generate_machine_list()

                # Set the previous format dictionary, and then update the current one.
                self.previous_format_dict = self.format_dict

                # Generate the format dictionary using the list of machines.
                self.format_dict = self.generate_format_dict(
                    machine_list=self.machine_list,
                    previous_format_dict=self.previous_format_dict,
                )

                # Generate the presence dictionary using the format dictionary and the previous format dictionary.
                self.presence_dict = self.generate_presence_dict(
                    format_dict=self.format_dict
                )

                # Update the Rich Presence.
                self.RPC.update(**self.presence_dict)

                # Print the current presence to the terminal.
                # [TODO] Print the presence dictionary more neatly
                pprint.pprint(self.presence_dict)
                print("--------------------")

            # Stop updating the Rich Presence if VirtualBox is not running.
            else:
                p.wait()
                os.kill(os.getpid(), 0)

            time.sleep(15)

    def generate_machine_list(self):

        # Initialize list to store machine information.
        machine_list = []

        # Get information for each machine.
        machines = self.virtualbox.machines
        machine_names = [machine.name for machine in machines]
        machine_states = [machine.state for machine in machines]
        machine_operating_systems = [machine.os_type_id for machine in machines]

        # Iterate through the machines and store information about them in the machine list.
        for machine_index in range(len(machines)):

            # Initialize dictionary to store machine information.
            machine_list.append({})

            # Obtain OS and architecture information.
            os_version, architecture = self.generate_os_and_architecture(
                machine_operating_systems[-1]
            )

            # Assign the corresponding information to the keys in the dictionary
            machine_list[-1]["name"] = machine_names[-1]
            machine_list[-1]["architecture"] = architecture
            machine_list[-1]["state"] = str(machine_states[-1])

            # Iterate through assets and find the correct OS.
            for os in self.assets["operating systems"]:

                # If the OS version is found in any of the OS dictionaries, set the version to that key.
                if os_version in self.assets["operating systems"][os]["versions"]:

                    machine_list[-1]["os"] = os
                    machine_list[-1]["os version"] = os_version

        return machine_list

    def generate_os_and_architecture(self, os_type_id: str):

        # Split OS type ID to obtain the OS and architecture.
        if "_" in os_type_id:

            self.oa_operating_system, self.oa_architecture = os_type_id.split("_", 1)

        # If an architecture is not stated, it is 32-bit.
        else:

            self.oa_operating_system = os_type_id
            self.oa_architecture = "32"

        return self.oa_operating_system, self.oa_architecture

    def generate_format_dict(
        self, machine_list: tuple[dict], previous_format_dict: dict
    ):

        # Store previous start time and remove it from the dictionary, to help with
        previous_start = previous_format_dict.pop("start")

        # Initialize dictionary to store Rich Presence formatting.
        format_dict = {}

        # Assume there is no machine active.
        format_dict["machine active"] = False

        # Iterate through machine dictionary and find a machine that is online.
        for machine in machine_list:

            if machine["state"] == "FirstOnline":

                # Recognize that the user is in a machine.
                format_dict["machine active"] = True

                # Fill the rest of the formatting dictionary with information from the machine dictionary.
                format_dict["machine name"] = machine["name"]
                format_dict["os name"] = machine["os"]
                format_dict["os version"] = machine["os version"]
                format_dict["os version name"] = self.assets["operating systems"][
                    machine["os"]
                ]["versions"][machine["os version"]]["name"]
                format_dict["os version image"] = self.assets["operating systems"][
                    machine["os"]
                ]["versions"][machine["os version"]]["image"]
                format_dict["architecture"] = machine["architecture"]
                format_dict["architecture image"] = machine["architecture"]

                # End the loop now that we have found the active machine.
                break

        format_dict["icon"] = "icon"

        # If the format dictionary has not changed, then use the same start time as last time.
        if format_dict == previous_format_dict:

            format_dict["start"] = previous_start

        # If the format dictionary has changed since the last loop, then reset the timer.
        else:

            # Set the start time of the Rich Presence to now.
            format_dict["start"] = time.time()

        return format_dict

    def generate_presence_dict(self, format_dict: dict):

        # Initialize dictionary to store the Rich Presence.
        presence_dict = {}

        # If there is an active machine, display it on the presence.
        if format_dict["machine active"] == True:

            # For each field in the config, set the Rich Presence to show that the user is in a machine.
            for field in self.config["In Machine"]:

                presence_dict[field] = self.config["In Machine"][field].format(
                    **format_dict
                )

            # Set the start time using the format dictionary.
            presence_dict["start"] = format_dict["start"]

        # For each field in the config, set the Rich Presence to show that the user is in the menu.
        else:

            # Fill each presence dictionary field with the corresponding formatting set by the user in the config.
            for field in self.config["In Menu"]:

                presence_dict[field] = self.config["In Menu"][field].format(
                    **format_dict
                )

            # If the user is in the menu, there is no need to show the time elapsed.
            presence_dict["start"] = None

        # Set all empty strings or empty lists to None.
        for field in presence_dict:

            if presence_dict[field] == "" or presence_dict[field] == []:

                presence_dict[field] = None

        return presence_dict


RichPresence()