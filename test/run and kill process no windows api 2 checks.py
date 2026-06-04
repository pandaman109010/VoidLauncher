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
    
    # 1. Snapshot windows before launching
    pre_existing_windows = get_visible_windows_by_exe(exe_name)
    
    print(f"Launching {exe_name}...")
    try:
        subprocess.Popen([app_path])
    except Exception as e:
        print(f"❌ Failed to launch {exe_name}: {e}")
        return
    
    # The 5-second window where you can now freely open other apps!
    time.sleep(5) 
    
    # 2. Snapshot windows after launching
    current_windows = get_visible_windows_by_exe(exe_name)
    
    # 3. Isolate newcomers
    new_windows = current_windows - pre_existing_windows
    
    # --- DOUBLE-VERIFICATION SAFEGUARD ---
    # We filter the new windows to ensure they strictly belong to our target EXE name
    our_verified_windows = set()
    for hwnd in new_windows:
        pid = ctypes.c_ulong()
        User32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_handle = Kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
        if proc_handle:
            buffer = ctypes.create_unicode_buffer(260)
            size = ctypes.c_ulong(260)
            Kernel32.QueryFullProcessImageNameW(proc_handle, 0, buffer, ctypes.byref(size))
            Kernel32.CloseHandle(proc_handle)
            
            # STRICT CHECK: It must be a newcomer AND match the exact EXE name
            if exe_name.lower() in buffer.value.lower():
                our_verified_windows.add(hwnd)

    # --- EXECUTE CLOSE ---
    if our_verified_windows:
        print(f"Sending polite close request to verified {exe_name} window(s)...")
        for hwnd in our_verified_windows:
            User32.PostMessageW(hwnd, 0x0010, 0, 0) # WM_CLOSE
        time.sleep(2)
        print(f"Clean close complete.\n")
    else:
        print(f"No specific verified window found for {exe_name}. Moving on...\n")

if __name__ == "__main__":
    # Test with Word—it will isolate the script's window perfectly!
    run_and_clean_kill(r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE")
    
    # Ready for your target app whenever you want to swap it:
    # run_and_clean_kill("auth.exe")