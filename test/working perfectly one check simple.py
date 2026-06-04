import subprocess
import time
import os
import ctypes

# Pull the exact 3 Windows functions we need
User32 = ctypes.windll.user32
Kernel32 = ctypes.windll.kernel32

def get_visible_windows_by_exe(exe_name):
    """Returns a set of window handles matching the executable name."""
    found_windows = set()
    
    # Define the callback function Windows requires to loop through windows
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    
    def scan_window(hwnd, lparam):
        # 1. Only look at windows that are actually visible on your desktop
        if User32.IsWindowVisible(hwnd):
            pid = ctypes.c_ulong()
            User32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            
            # 2. Open the process just enough to see what its EXE is called
            proc_handle = Kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
            if proc_handle:
                buffer = ctypes.create_unicode_buffer(260)
                size = ctypes.c_ulong(260)
                
                # Get the real EXE name running this window
                Kernel32.QueryFullProcessImageNameW(proc_handle, 0, buffer, ctypes.byref(size))
                Kernel32.CloseHandle(proc_handle)
                
                if exe_name.lower() in buffer.value.lower():
                    found_windows.add(hwnd)
        return True

    # Tell Windows to run our scan_window function across every open window
    User32.EnumWindows(WNDENUMPROC(scan_window), 0)
    return found_windows

def run_and_clean_kill(app_path):
    exe_name = os.path.basename(app_path)
    
    # 1. Snapshot windows before launching ours
    pre_existing_windows = get_visible_windows_by_exe(exe_name)
    
    print(f"Launching {exe_name}...")
    subprocess.Popen([app_path])
    
    # Give the app time to fully load its window
    time.sleep(5) 
    
    # 2. Snapshot windows after launching
    current_windows = get_visible_windows_by_exe(exe_name)
    
    # 3. Find the exact newcomer window handle
    our_new_windows = current_windows - pre_existing_windows
    
    if our_new_windows:
        print("Found the exact automated window! Sending polite close request...")
        for hwnd in our_new_windows:
            # 0x0010 is the universal Windows message code for WM_CLOSE (Clicking the X button)
            User32.PostMessageW(hwnd, 0x0010, 0, 0)
        
        time.sleep(2)
        print("Clean close complete.")
    else:
        print("No specific window found.")

if __name__ == "__main__":
    # Test with Word—it will isolate the script's window perfectly!
    run_and_clean_kill(r"C:\Users\Jimmy\AppData\Local\Programs\Ente Auth\auth.exe")
    
    # Ready for your target app whenever you want to swap it:
    # run_and_clean_kill("auth.exe")