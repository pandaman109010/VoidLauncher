import subprocess
import time
import ctypes
from ctypes import wintypes

# Load native Windows API utilities
User32 = ctypes.WinDLL('user32', use_last_error=True)
Kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

WM_CLOSE = 0x0010

def get_window_handles_by_exe(exe_name):
    """Returns a list of window handles matching a specific executable name."""
    handles = []
    
    # Callback function for EnumWindows
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    
    def enum_windows_callback(hwnd, lparam):
        if User32.IsWindowVisible(hwnd):
            pid = wintypes.DWORD()
            User32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            
            # Open the process to check its executable name
            process_handle = Kernel32.OpenProcess(0x0400 | 0x0010, False, pid.value)
            if process_handle:
                buffer = ctypes.create_unicode_buffer(260)
                size = wintypes.DWORD(260)
                # Query full process image name
                try:
                    # For compatibility across different Windows process types
                    ctypes.windll.kernel32.QueryFullProcessImageNameW(process_handle, 0, buffer, ctypes.byref(size))
                    if exe_name.lower() in buffer.value.lower():
                        handles.append(hwnd)
                except:
                    pass
                Kernel32.CloseHandle(process_handle)
        return True

    User32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
    return handles

def run_and_clean_kill(app_path):
    import os
    exe_name = os.path.basename(app_path)
    
    # 1. Take a snapshot of windows matching this EXE *before* we launch ours
    pre_existing_windows = set(get_window_handles_by_exe(exe_name))
    
    print(f"Launching {exe_name}...")
    process = subprocess.Popen([app_path])
    
    # Let the application fully load its window layout
    time.sleep(5)
    
    # 2. Take a snapshot *after* launching
    current_windows = set(get_window_handles_by_exe(exe_name))
    
    # The difference is the EXACT window(s) our script just opened!
    our_new_windows = current_windows - pre_existing_windows
    
    if our_new_windows:
        print(f"Found specific window handle(s) for our instance. Sending clean close request...")
        for hwnd in our_new_windows:
            # PostMessage sends a clean, un-forced "X button click" message to just this window
            User32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            
        # Give it a moment to run its internal saving script
        time.sleep(2)
        print("Clean close request completed.")
    else:
        print("Could not isolate a specific visual window. Falling back to standard process closure...")
        try:
            # If it's a completely headless background app (like auth.exe might be),
            # fall back to standard PID management.
            process.terminate()
        except:
            pass

if __name__ == "__main__":
    # TEST 1: Will close ONLY this specific Word window, leaving your other tabs completely untouched!
    # run_and_clean_kill(r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE")
    
    # TEST 2: Works perfectly fine on background tools or target binaries
    run_and_clean_kill(r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE")
