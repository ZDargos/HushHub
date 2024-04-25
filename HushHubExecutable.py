import subprocess
import uuid
import sys, os
import customtkinter as ctk
from threading import Thread
import time
from PIL import Image
from tkinter import PhotoImage

good_blue = "#010c20"
title_font = ("Helvetica", 36, "bold")
section_title_font = ("Helvetica", 15,"bold")
def install_package(package_name):
    """Install a Python package using pip."""
    # Use the appropriate pip command based on the Python version
    pip_command = "pip"
    if sys.version_info.major == 3:
        pip_command = "pip3"

    # Run the pip install command
    subprocess.run([pip_command, "install", package_name])


def install_arduino_library(library_name):
    """Install an Arduino library using Arduino CLI."""
    # Define the command to install the library
    arduinoPath = os.getcwd() + "\\arduino-cli_0.36.0-rc.2_Windows_64bit\\arduino-cli"
    command = [arduinoPath, 'lib', 'install', library_name]

    try:
        # Run the command using subprocess.run
        subprocess.run(command, check=True)
        print(f"Successfully installed the library: {library_name}")
    except subprocess.CalledProcessError as e:
        # Handle any errors that occur during the installation
        print(f"Failed to install the library: {library_name}. Error: {e}")


"""Test if imports exist, if not need to install them"""
try:
    from win32api import *
except ModuleNotFoundError:
    print("pywin32 not installed!")
    install_package("pywin32")
    from win32api import *
from win32gui import *  #Package within pywin32 no need to check
import win32con         #Package within pywin32 no need to check

try:
    import paho.mqtt.client as paho
except ModuleNotFoundError:
    print("paho-mqtt library not installed!")
    install_package("paho-mqtt<2.0.0")
    import paho.mqtt.client as paho


HushID = ""  # AlertID used to make sure you only receive alerts from this specific alert number
threads = []
clients = []
def modify_HushID(str):
    global HushID
    HushID = str

class WindowsBalloonTip:
    '''Class used to create and activate windows alerts on command'''
    def __init__(self, app_name, icon_path=None):
        message_map = {
            win32con.WM_DESTROY: self.OnDestroy,
        }
        wc = WNDCLASS()
        hinst = wc.hInstance = GetModuleHandle(None)
        unique_class_name = "PythonTaskbar" + app_name + str(uuid.uuid4())  # Append a unique UUID to the class name
        wc.lpszClassName = unique_class_name
        wc.lpfnWndProc = message_map
        try:
            classAtom = RegisterClass(wc)  # Attempt to register the class
        except Exception as e:
            print(f"Error registering class: {e}")
            return
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = CreateWindow(classAtom, app_name, style,
                                 0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
                                 0, 0, hinst, None)
        UpdateWindow(self.hwnd)

        if icon_path is None:
            icon_path = os.path.abspath(os.path.join(sys.path[0], "balloontip.ico"))
        icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
        try:
            self.hicon = LoadImage(hinst, icon_path,
                                   win32con.IMAGE_ICON, 0, 0, icon_flags)
        except Exception as e:
            self.hicon = LoadIcon(0, win32con.IDI_APPLICATION)

        flags = NIF_ICON | NIF_MESSAGE | NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER+20, self.hicon, "tooltip")
        Shell_NotifyIcon(NIM_ADD, nid)

    def show_notification(self, title, msg):
        """Function to display the notification"""
        Shell_NotifyIcon(NIM_MODIFY,
                         (self.hwnd, 0, NIF_INFO, win32con.WM_USER+20,
                          self.hicon, title, msg, 200, title))

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        Shell_NotifyIcon(NIM_DELETE, nid)
        PostQuitMessage(0)

def balloon_tip(app_name, title, msg):
    '''Function used to utilze windowsballoontip class to send a windows alert with title [title] and message [msg]'''
    notifier = WindowsBalloonTip(app_name)
    notifier.show_notification(title, msg)
    # Sleep or wait for a condition before destroying, depending on your use case
    # Here, a delay to allow the notification to be visible before the script ends
    time.sleep(3)

def validate_PeakThresh(new_value):
    '''
    Validation function to impose limits on inputs for PeakThreshold
    '''
    if new_value == "":
        return True  # Allow empty input
    try:
        i = int(new_value)
        if(i <= 500 and i > 40 and len(new_value) < 4):
            return True
        else: return False

    except ValueError:
        return False

def validate_ThreshTime(new_value):
    '''
    Validation function to impose limits on inputs for ThreshTime
    '''
    if new_value == "":
        return True  # Allow empty input
    try:
        i = int(new_value)
        if(i > 0 and i <= 86400 and len(new_value) < 6):
            return True
        else: return False

    except ValueError:
        return False
def validate_Num_Peaks_Permitted(new_value):
    '''
    Validation function to impose limits on inputs for ThreshTime
    '''
    if new_value == "":
        return True  # Allow empty input
    try:
        i = int(new_value)
        if(i >= 0 and i <= 86400 and len(new_value) < 6):
            return True
        else: return False

    except ValueError:
        return False

def validate_Anything(new_value):
    return True
def connectMQTT(HushID):
    client = initializeClient(HushID)
    try:
        clients.append(client)
        client.loop_forever()
    except Exception as e:
        print(f"Error running loop: {e}")
        while (True):
            continue
def startConnect(HushID_input):
    modify_HushID(HushID_input)
    thread = Thread(target=lambda: connectMQTT(HushID))
    thread.start()
    threads.append(thread)

def endConnection():
    for client in clients:
        client.disconnect()
def on_close():
    for thread in threads:
        thread.join(timeout=0)
    endConnection()
    root.destroy()
def isThreshTime(str):
    if str == "ThreshTime":
        return 1
    return 1/1000
def saveVals(FrameList):
    variables_to_modify = {}
    sketch_path = os.getcwd() + "\\MicrophoneReader2\\MicrophoneReader2.ino"  # Get path to arduino file
    for frame in FrameList:
        for widget in frame.winfo_children():
            # Check if the widget is an entry widget
            if isinstance(widget, ctk.CTkEntry) or isinstance(widget, ctk.CTkSlider):
                # Get the value from the entry widget
                varName = widget.winfo_name
                varVal = widget.get()
                if varVal == "" or varVal == '':
                    continue
                if varName == "message" or varName == "AlertID":
                    variables_to_modify[f"String {varName}"] = '"' + varVal + '"'
                elif varName == "ssid" or varName == "password":
                    variables_to_modify[f"const char* {varName}"] = '"' + varVal + '"'
                else:
                    variables_to_modify[f"int {varName}"] =  int(varVal) * int((1000 * isThreshTime(varName)))
    modify_sketch(sketch_path,variables_to_modify)

def enableFrame(frame):
    frame.place(relx=0.5,rely=0.47,anchor="center")
def disableFrame(frame):
    frame.place_forget()

def make_Variable_Frame(master,name,relx,rely,label_text,label_subText,currVal,validation):
    Frame = ctk.CTkFrame(master, width=300, height=100, border_width=1, border_color="black")
    Frame.configure(bg_color=good_blue, fg_color="#031b3e")
    Frame.place(relx=relx, rely=rely, anchor="w")

    # Number of Peaks
    label = ctk.CTkLabel(Frame, text=label_text, font=section_title_font,
                                           text_color="#ababab")
    label.place(relx=0.05, rely=0.15, anchor="w")
    label_Max = ctk.CTkLabel(Frame, text=label_subText, font=section_title_font,
                             text_color="#ababab")
    label_Max.place(relx=0.05, rely=0.75, anchor="w")
    entry = ctk.CTkEntry(Frame, placeholder_text=f"{currVal}",
                                           validate="key", validatecommand=(validation, "%P"),
                                           width=270, height=30, fg_color="#031b3e")
    entry.place(relx=0.5, rely=0.4, anchor="center")
    entry.winfo_name = name
    return Frame

def read_entry_value(Frame):
    # Iterate through all children of the frame
    for child in Frame.winfo_children():
        # Check if the child widget is an entry
        if isinstance(child, ctk.CTkEntry):
            # Retrieve and print the value of the entry
            entry_value = child.get()
            return entry_value
def app_init():
    AllFrames = []
    sketch_path = os.getcwd() + "\\MicrophoneReader2\\MicrophoneReader2.ino"  # Get path to arduino file
    AllVars = {"message", "PeakThreshold", "ThreshTime", "NumPeaksPermitted", "ssid", "password", "AlertID"}
    AllVars = read_vars(sketch_path, AllVars)
    ctk.set_appearance_mode("dark")  # Or use system / light
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1920x1080")  # Resolution

    root.wm_title("HushHub")
    root.iconbitmap(os.getcwd() + "\\Images\\HushHubLogo.ico")


    Frame_Home = ctk.CTkFrame(root)
    Frame_Home.pack(padx=0, pady=0, fill="both", expand=True)
    Frame_Home.configure(bg_color=good_blue,fg_color=good_blue)

    Frame_Options = ctk.CTkFrame(root,width=1000,height=800,border_width=2,border_color="black")
    Frame_Options.winfo_name = "Options"
    Frame_Options.configure(bg_color=good_blue,fg_color="#021534")

    validation_PeakThresh = root.register(validate_PeakThresh)
    validation_ThreshTime = root.register(validate_ThreshTime)
    validation_NumPeaksPermitted = root.register(validate_Num_Peaks_Permitted)
    validation_any = root.register(validate_Anything)
    root.protocol("WM_DELETE_WINDOW", on_close)


    '''
    Define HushID input and Connect Button
    '''
    # HushID
    custom_font = ("Helvetica", 34)

    '''
    Loading all images used in menu
    '''
    button_image = ctk.CTkImage(dark_image=Image.open(os.getcwd() + "\\Images\\Connect.png"),size=(113,113))
    options_image = ctk.CTkImage(dark_image=Image.open(os.getcwd() + "\\Images\\Options.png"),size=(50,50))
    bg_image = ctk.CTkImage(dark_image=Image.open(os.getcwd() + "\\Images\\HomeBG.png"),size=(1920,1080))
    bg_cyan = ctk.CTkImage(dark_image=Image.open(os.getcwd() + "\\Images\\BG_Cyan.png"),size=(500,800))
    bg_navy = ctk.CTkImage(dark_image=Image.open(os.getcwd() + "\\Images\\BG_Navy.png"), size=(500, 800))
    close_image = ctk.CTkImage(dark_image=Image.open(os.getcwd() + "\\Images\\close.png"),size=(35,35))

    '''
    Establishing all backgrounds
    '''
    background_label = ctk.CTkLabel(Frame_Home, image=bg_image, text="")
    background_label.place(relx=0.5, rely=0.5, relwidth=1, relheight=1, anchor="center")

    background_label_option1 = ctk.CTkLabel(Frame_Options, image=bg_cyan, text="")
    background_label_option1.place(relx=0, rely=.5, relwidth=.2, relheight=1, anchor="w")


    '''
    Defining Home Frame
    '''
    entry_HushID = ctk.CTkEntry(Frame_Home,fg_color="#ffffff", placeholder_text=f"HushHubID: {AllVars['AlertID']}",font=custom_font,text_color="#9a9da1", placeholder_text_color="#9a9da1",width=400, border_color="black",border_width=4)
    entry_HushID.place(relx=0.3, rely=0.4, anchor="center")
    button_connect = ctk.CTkButton(Frame_Home,corner_radius=100, border_width=2, border_color="#406de2", text="",fg_color="transparent", image=button_image,font=custom_font, command=lambda : startConnect(entry_HushID.get()),width=50,height=100)
    button_connect.place(relx=0.3, rely=0.55, anchor="center")

    button_options = ctk.CTkButton(Frame_Home,corner_radius=1000,border_width=2, bg_color="#27f7cf", fg_color="#27f7cf",border_color="#010c20", text="",image=options_image,font=custom_font,width=25,height=50,command=lambda:enableFrame(Frame_Options))
    button_options.place(relx=0.93, rely=0.07, anchor="center")


    '''
    Creating the options menu
    '''


    #Title card top left
    label_options = ctk.CTkLabel(Frame_Options, text="Options",font=title_font,text_color="#201313", bg_color="#1db5a3")
    label_options.place(relx=0.03, rely=0.1, anchor="w")

    button_closeOptions = ctk.CTkButton(Frame_Options, corner_radius=1000, border_width=2, bg_color="#021534",
                                   fg_color="#031b3e", border_color="#010c20", text="", image=close_image,
                                width=25, height=20, command=lambda: disableFrame(Frame_Options))
    button_closeOptions.place(relx=0.95, rely=0.05, anchor="center")
    '''
    Establish all labels and entries to determine arduino code values
    '''

    #Frame that houses message editor box
    Frame_message = ctk.CTkFrame(Frame_Options,width=300,height=100,border_width=1,border_color="black")
    Frame_message.configure(bg_color=good_blue, fg_color="#031b3e")
    Frame_message.place(relx=.6,rely=.1,anchor="w")
    AllFrames.append(Frame_message)

    # Message
    label_msg = ctk.CTkLabel(Frame_message, text="ALERT MESSAGE",font=section_title_font,text_color="#ababab")
    label_msg.place(relx=0.05, rely=0.15, anchor="w")
    entry_msg = ctk.CTkEntry(Frame_message, placeholder_text=f"{AllVars['message']}",width=270,height=70,fg_color="#031b3e")
    entry_msg.place(relx=0.5, rely=0.6, anchor="center")
    entry_msg.winfo_name = "message"

    Frame_numPeaks = make_Variable_Frame(master=Frame_Options,name="NumPeaksPermitted", relx=.25,rely=.1,label_text="NUMBER OF PEAKS PERMITTED",label_subText="MIN = 0   MAX = 86400",
                                         currVal=AllVars['NumPeaksPermitted'],validation=validation_NumPeaksPermitted)
    AllFrames.append(Frame_numPeaks)
    Frame_ThreshTime = make_Variable_Frame(master=Frame_Options,name="ThreshTime", relx=.25,rely=.25,label_text="SECONDS BEFORE RESET",label_subText="MIN = 1   MAX = 86400",
                                         currVal=(int(AllVars['ThreshTime'])//1000),validation=validation_ThreshTime)
    AllFrames.append(Frame_ThreshTime)
    mess = "i.e. COM4"
    Frame_ComPort = make_Variable_Frame(master=Frame_Options,name="COM_Port", relx=.25,rely=.4,label_text="COM PORT",label_subText="COM PORT CONNECTED TO HUSHHUB",
                                         currVal=mess,validation=validation_any)
    Frame_AlertID = make_Variable_Frame(master=Frame_Options, name="AlertID", relx=.25, rely=.55, label_text="ALERT ID",
                                        label_subText="MAKE YOUR ID WHATEVER YOU WANT",
                                        currVal=(AllVars['AlertID']), validation=validation_any)

    AllFrames.append(Frame_AlertID)
    # Frame that houses wifi editor box
    Frame_WiFi = ctk.CTkFrame(Frame_Options, width=300, height=200, border_width=1, border_color="black")
    Frame_WiFi.configure(bg_color=good_blue, fg_color="#031b3e")
    Frame_WiFi.place(relx=.6, rely=.3125, anchor="w")
    AllFrames.append(Frame_WiFi)
    # SSID
    label_WiFi = ctk.CTkLabel(Frame_WiFi, text="WIFI:", font=section_title_font, text_color="#ababab")
    label_WiFi.place(relx=0.05, rely=0.075, anchor="w")

    label_WiFi_ssid = ctk.CTkLabel(Frame_WiFi, text="SSID:", font=section_title_font, text_color="#ababab")
    label_WiFi_ssid.place(relx=0.05, rely=0.275, anchor="w")

    entry_WiFi_ssid = ctk.CTkEntry(Frame_WiFi, placeholder_text=f"{AllVars['ssid']}", width=270, height=30,
                             fg_color="#031b3e")
    entry_WiFi_ssid.winfo_name = "ssid"
    entry_WiFi_ssid.place(relx=0.5, rely=0.425, anchor="center")

    # PASSWORD
    label_WiFi_pass = ctk.CTkLabel(Frame_WiFi, text="Password:", font=section_title_font, text_color="#ababab")
    label_WiFi_pass.place(relx=0.05, rely=0.625, anchor="w")
    entry_WiFi_pass = ctk.CTkEntry(Frame_WiFi, placeholder_text=f"{AllVars['password']}", width=270, height=30,
                                   fg_color="#031b3e")
    entry_WiFi_pass.winfo_name = "password"
    entry_WiFi_pass.place(relx=0.5, rely=0.775, anchor="center")

    # Frame for PeakThreshold
    Frame_PeakThreshold = ctk.CTkFrame(Frame_Options, width=750, height=100, border_width=1, border_color="black")
    Frame_PeakThreshold.configure(bg_color=good_blue, fg_color="#031b3e")
    Frame_PeakThreshold.place(relx=.225, rely=.9, anchor="w")
    label_PeakThreshold = ctk.CTkLabel(Frame_PeakThreshold, text=f"Sound Level :   {AllVars['PeakThreshold']} ",font=("Helvetica",20,"bold"), text_color="#ababab")
    label_PeakThreshold.place(relx=.015, rely=.5, anchor="w")


    # Peak Threshold Slider
    def update_Slider(value):
        label_PeakThreshold.configure(text=f"Sound Level :   {int(value)} ")
        AllFrames.append(Frame_PeakThreshold)
    slider_PeakThreshold = ctk.CTkSlider(Frame_PeakThreshold,button_length=2,width=500,height=25,from_=40, to=500,command=update_Slider,progress_color="#1db5a3")
    slider_PeakThreshold.set(int(AllVars['PeakThreshold']))
    slider_PeakThreshold.winfo_name = "PeakThreshold"
    slider_PeakThreshold.place(relx=0.6,rely=.5,anchor="center")

    '''
    Define Button To Compile and Upload Arduino Code
    '''
    button_save = ctk.CTkButton(Frame_Options, text="Save Changes",command=lambda:saveVals(AllFrames),bg_color="#1db5a3",width=150,height=40,
                                border_width=2,border_color="black")
    button_save.place(relx=0.025, rely=0.2, anchor="w")
    button_compile = ctk.CTkButton(Frame_Options, text= "Compile and Upload", command=lambda: compile_and_upload_sketch(sketch_path,read_entry_value(Frame_ComPort)),bg_color="#1db5a3",width=150,height=40,
                                border_width=2,border_color="black")
    button_compile.place(relx=0.025, rely=0.3, anchor="w")

    return root

def on_connect(client, userdata, flags, rc):
    '''Pointer function to tell client what to do when it connects to server'''
    c_id = str(client._client_id.decode("utf-8"))
    print("Connected to " + c_id + " with result code "+str(rc))
    print(HushID)
    client.subscribe("Alerts" + HushID + "/#",qos=1)  # Your topic

def on_message(client, userdata, msg):
    '''Pointer function to tell client how to interpret received messages'''
    message = msg.payload.decode()
    print(f"Message Received:  {message}")
    app_name = "HushHub"
    title = "Hush Hub Notification"
    balloon_tip(app_name, title, message)
    if(message == client._client_id.decode("utf-8")):
        pass
def on_disconnect(client, userdata, rc):
    print("Disconnected with " + str(rc))

def initializeClient(HushID):
    try:
        # Create a new MQTT client
        client = paho.Client(client_id="HushHub: " + str(HushID))
    except Exception as e:
    # Print an error message if the initialization fails
        print(f"Error initializing client: {e}")

    # Return None if an error occurs during client initialization

    # Proceed with the rest of the client setup
    client.username_pw_set("HushHubS", "DarvacsHubS1") # User-pass for subscribe only access to server (read-only)
    client.tls_set(tls_version=paho.ssl.PROTOCOL_TLS)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Connect to the MQTT broker
    client.connect("7a9481a885f646fda619cbcfe91f0802.s1.eu.hivemq.cloud", 8883)

    # Return the initialized client if successful
    return client



# Compile and upload the sketch using arduino-cli
def compile_and_upload_sketch(sketch_path, arduino_port):
    # Compile the sketch
    board_type = "esp8266:esp8266:d1_mini"  # Known board type used in device, change if necessary
    arduinoPath = os.getcwd() + "\\arduino-cli_0.36.0-rc.2_Windows_64bit\\arduino-cli"
    compile_command = f"{arduinoPath} compile -u --fqbn {board_type} --port {arduino_port} {sketch_path}"
    print(compile_command)

    """Try to run arduino-cli compile and upload command"""
    try:
        compile_process = subprocess.run(compile_command, shell=True, check=True,capture_output = True)
    except Exception as e:
        """If it fails, most likely due to incomplete library installation."""
        install_arduino_library("PubSubClient")
        install_arduino_library("NTPClient")
        install_arduino_library("ESP8266WiFi")
        install_arduino_library("WiFiClientSecure")
        compile_process = subprocess.run(compile_command, shell=True, check=True, capture_output=True)
    # Upload the sketch if compilation is successful
    if compile_process.returncode == 0:
        print(f"Successfully uploaded sketch to {arduino_port}")
    else:
        print("Failed to compile the sketch")
def clear_terminal():
    # Clear the terminal screen depending on the operating system
    os.system('cls' if os.name == 'nt' else 'clear')
def read_vars(sketch_path, variables):
    """
    :param sketch_path: Path to arduino code
    :param variables: variables you want to retrieve values for
    :return: dictionary with each variable and current value
    """
    var_vals = {}
    with open(sketch_path, 'r') as file:
        sketch_lines = file.readlines()
    for line in sketch_lines:
        for var in variables:
            if (" " + var + " = ") in line:
                var_vals[var] = line[line.index("=")+2:line.index(";")]
    return var_vals
def modify_sketch(sketch_path, variables):
    """ Modify the variables [variables] in arduino file at [sketch_path]"""
    """ Open the arduino file as a read instance """
    with open(sketch_path, 'r') as file:
        sketch_lines = file.readlines()

    """Read through arduino file with a new instance of it as a writable file, if a line matches a variable ot be changed, change it"""
    with open(sketch_path, 'w') as file:
        for line in sketch_lines:
            for var_name, var_value in variables.items():
                # If the line contains the variable name, replace the value
                if (var_name + " = ") in line:
                    line = f"{var_name} = {var_value};\n"
            file.write(line)

def setUpArduino():
    """
        Logic to change variables within the arduino file
        Currently editable values:
        message
        PeakThreshold
        ThreshTime
        NumPeaksPermitted
    """

    if (input("Do you want to make any changes? (y/n) ") == "y"):
        sketch_path = os.getcwd() + "\\MicrophoneReader2\\MicrophoneReader2.ino"  # Get path to arduino file
        AllVars = {"message", "PeakThreshold", "ThreshTime", "NumPeaksPermitted", "ssid", "password"}
        variables_to_modify = {}
        AllVars = read_vars(sketch_path, AllVars)
        while (True):
            clear_terminal()
            print("\n-------------------------------\nVariables: [Case Sensitive]")
            print(f"message = {AllVars['message']}         |    Determines the message sent as the Alert\n"
                  f"PeakThreshold = {AllVars['PeakThreshold']}     |    The 'loudness' level that determines what is too loud (100-500)\n"
                  f"ThreshTime = {AllVars['ThreshTime']}        |    The cooldown time (in seconds) where if you are quiet for this amount of time your counter resets\n"
                  f"NumPeaksPermitted = {AllVars['NumPeaksPermitted']} |    Number of 'too louds' permitted in ThreshTime before an alert is sent\n"
                  f"ssid = {AllVars['ssid']}             | Wifi Name\n"
                  f"password = {AllVars['password']}     | Wifi Password\n"
                  )
            if (input("Do you want to change any values? (y/n) ") == "n"): break

            varName = input("-------------------------------\nEnter the name of the variable to modify: ")
            if (varName in AllVars):
                if varName == "message":
                    varVal = str(input(f"Enter the new value of {varName}: "))
                    variables_to_modify["String " + varName] = '"' + varVal + '"'
                    AllVars[varName] = varVal
                elif varName == "ssid" or varName == "password":
                    varVal = str(input(f"Enter the new value of {varName}: "))
                    variables_to_modify["const char* " + varName] = '"' + varVal + '"'
                    AllVars[varName] = varVal
                else:
                    varVal = int(input(f"Enter the new value of {varName}: "))
                    if varName == "ThreshTime": varVal *= 1000
                    variables_to_modify["int " + varName] = varVal
                    AllVars[varName] = varVal
            else:
                print("Invalid Variable Name\n-------------------------------\n")
        chgID = input("Do you want to update the HushHub device's current working ID to the same? (y/n) ")
        if chgID == "y":
            variables_to_modify["String AlertID"] = '"' + HushID + '"'
        print(variables_to_modify)
        if (len(variables_to_modify) > 0):
            # Prompt the user for the port the Arduino is connected to
            arduino_port = input("Enter the port where the Arduino is connected (e.g., COM3 or /dev/ttyUSB0): ")

            modify_sketch(sketch_path, variables_to_modify)
            compile_and_upload_sketch(sketch_path, arduino_port)



# def startWords():
#     thread = Thread(target=printWords)
#     thread.start()

def change_Resolution(root, res):
    root.geometry(res)

if __name__ == '__main__':
    root = app_init()
    root.mainloop()
