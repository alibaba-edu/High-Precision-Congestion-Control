#!/usr/bin/env python3
import sys
import os

# Add the extracted waf library to path
waf_dir = os.path.join(os.getcwd(), '.waf-1.7.11-edc6ccb516c5e3f9b892efc9f53a610f')
sys.path.append(waf_dir)

from waflib import Scripting, Context

# Define constants expected by waf (just in case)
Context.WAFVERSION="1.7.11"
Context.HEXVERSION=0x1070b00

# Scripting.waf_entry_point(current_directory, version, wafdir)
Scripting.waf_entry_point(os.getcwd(), "1.7.11", waf_dir)
