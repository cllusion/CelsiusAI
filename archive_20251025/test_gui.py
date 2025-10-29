#!/usr/bin/env python3
"""
Celsius AI Server Hub - GUI Diagnostic Test
Tests if the graphical interface components are working properly
"""

import tkinter as tk
from tkinter import ttk
import sys
import os


def test_gui_components():
    """Test GUI components to diagnose black screen issue"""
    print("🔍 CELSIUS AI SERVER HUB - GUI DIAGNOSTIC TEST")
    print("=" * 50)

    try:
        print("1️⃣ Testing Tkinter root window creation...")
        root = tk.Tk()
        root.title("🔍 GUI Test - Celsius AI")
        root.geometry("600x400")
        root.configure(bg="#2d2d2d")
        print("   ✅ Root window created successfully")

        print("2️⃣ Testing TTK styles...")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#2d2d2d", foreground="#ffffff")
        style.configure("TButton", background="#4d4d4d", foreground="#ffffff")
        print("   ✅ TTK styles configured successfully")

        print("3️⃣ Testing frame creation...")
        main_frame = ttk.Frame(root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        print("   ✅ Main frame created successfully")

        print("4️⃣ Testing label creation...")
        title_label = ttk.Label(main_frame, text="🛡️ Celsius AI - GUI Test", font=("Arial", 16, "bold"))
        title_label.pack(pady=20)
        print("   ✅ Title label created successfully")

        print("5️⃣ Testing button creation...")
        test_button = ttk.Button(
            main_frame, text="✅ Test Button - Click Me!", command=lambda: print("   🎯 Button clicked!")
        )
        test_button.pack(pady=10)
        print("   ✅ Test button created successfully")

        print("6️⃣ Testing hamburger menu components...")

        # Create hamburger menu container
        menu_frame = ttk.Frame(main_frame)
        menu_frame.pack(fill="x", pady=20)

        hamburger_btn = ttk.Button(menu_frame, text="☰", width=3)
        hamburger_btn.pack(side="left")

        restart_btn = ttk.Button(menu_frame, text="🔄", width=3)
        restart_btn.pack(side="right")

        print("   ✅ Hamburger menu components created successfully")

        print("7️⃣ Testing text widget...")
        status_text = tk.Text(main_frame, height=8, bg="#1a1a1a", fg="#ffffff", font=("Consolas", 10))
        status_text.pack(fill="both", expand=True, pady=(20, 0))

        status_text.insert(
            "1.0",
            """
✅ GUI Component Test Results:

🟢 Root Window: Working
🟢 TTK Styles: Working  
🟢 Frames: Working
🟢 Labels: Working
🟢 Buttons: Working
🟢 Hamburger Menu: Working
🟢 Text Widget: Working

🎉 All GUI components are functional!

If you can see this text, the GUI system is working properly.
The black screen issue in the Server Hub might be related to:
- Authentication initialization
- Content loading timing
- Import issues

Try restarting the Server Hub now.
        """,
        )
        status_text.config(state="disabled")

        print("   ✅ Text widget created successfully")

        print("\n🎉 GUI DIAGNOSTIC COMPLETE!")
        print("   All GUI components are working properly.")
        print("   The test window should be visible now.")
        print("   Close the test window to continue.")

        # Add close button
        close_button = ttk.Button(main_frame, text="🚪 Close Test Window", command=root.destroy)
        close_button.pack(pady=10)

        # Show the test window
        root.mainloop()

        print("\n✅ GUI test completed successfully!")

    except Exception as e:
        print(f"\n❌ GUI test failed: {str(e)}")
        print("   This indicates a problem with the GUI system.")
        return False

    return True


if __name__ == "__main__":
    success = test_gui_components()
    if success:
        print("\n🚀 GUI system is working - Server Hub should function properly")
    else:
        print("\n⚠️ GUI system has issues - Server Hub may not work correctly")
