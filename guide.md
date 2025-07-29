
# **Hacking Older Garmins**: Modifying firmware on the Garmin Forerunner 35


As an avid runner and cyclist, I recently upgraded from my 7-year-old
Garmin Forerunner 35 to a Forerunner 255. Like any curious hacker, I
decided to tamper with my old watch to see what I could modify. Finding
limited up-to-date resources about this older device, I figured I'd
document my research to make Garmin hacking more accessible.

This guide will document my journey with the Garmin Forerunner 35
specifically, but most of the **Firmware Modification** section is
relevant to *any* Garmin using the RGN update file format, which is most
older Garmins.

# Methods

There are two approaches to "hacking" the Garmin Forerunner 35:
modifying the actual firmware and pushing the modified firmware in an
update, or directly modifying system files.

## Direct Filesystem Modification

When you plug the Forerunner 35 into Garmin Express, the device's
filesystem appears under USB devices. Key folders include `ACTIVITY`
(containing workout FIT files), various other folders containing
configuration FIT files, and a `TEXT` folder with `.LNG` language files.

### FIT Files

Unlike FIT files for workouts which contain waypoints and other workout
data, configuration FIT files for the Garmin contain a \"header\"
section with some device information such as the Unit ID, then their
various config options. These files are in a binary format but can be
converted to CSV using Garmin's [FIT CSV
Tool](https://developer.garmin.com/fit/fitcsvtool/). From my testing,
tampering with the header section showed no actual changes on the
device. Beyond that, most of the config options are just device settings
you can change from the watch itself.

### LNG Files

LNG files contain program strings in various languages. There's no
validation on the strings, so you can change them freely---just keep the
file header intact and don't change the overall file length, or the
string offsets will be wrong and your device becomes unreadable (if you
mess this up, you can always factory reset the watch to go back).

I attempted a buffer overflow by removing strings entirely, but it just
produced NULL bytes for all strings instead.

So the LNG file approach lets you modify strings, but what about actual
functionality? Or changing strings for the default language, which has
no LNG file?

## Firmware Modification

Based on Herbert Oppmann's analysis (see Acknowledgements), RGN files
serve as Garmin "update files" containing various sections called
records. Each record has a header specifying its type and data size. The
process of patching firmware on the Garmin looks like this:


1.  Make modifications to the RGN file (how to modify it is what this
    section deals with)

2.  Plug the watch into your computer, and drag the modified RGN file
    into the main folder. Rename it to GUPDATE.rgn

3.  Unplug the watch, and you should get prompted to Install an update.

I built a tool to parse RGN files (based on an old C RGN parsing tool I
found, see Acknowledgements) that returns headers, offsets, and other
relevant information for each record. Running it on a Forerunner 35
firmware file from GMapTools revealed that the actual firmware is in the
region record with ID 14:


![image](https://github.com/jack898/rgntool/raw/main/imgs/RGNToolOutput.png)\
_Output from RGNTool on a sample RGN_



Exploring the firmware record, I found XML-like content, strings, and
lots of source file paths. Feeling a bit lost, I simply identified a
string showing the device's IC and M/N numbers, that I knew was visible
on the watch settings. I changed a digit and uploaded the patched RGN.
Surprisingly, it worked! When I viewed the System information page on
the watch, these new numbers were shown.


![image](https://github.com/jack898/rgntool/raw/main/imgs/beforeChange.png)
![image](https://github.com/jack898/rgntool/raw/main/imgs/afterChange.png)

_The process of modifying strings in the RGN file, using HxD_


I then tried to change some strings, such as the above example. However,
attempting to change text strings failed---the updates seemed to
install, but the strings did not appear modified on the device. It
seemed like an integrity check was allowing those single-digit changes,
but not whole strings.

That's when found an old GitHub repo with what looked like actual
internal Garmin C code, and it contained a `signed_updates` folder,
suggesting some kind of private key signature being used for updates. I
was beginning to lose hope, but then I discovered Herbert Oppmann's BIN
format documentation (see Acknowledgements). Oppmann to the rescue
again!

I reviewed his documentation, and found that my firmware section had FF
padding to `0x0200`, indicating load address `0x1000`. I disassembled
using ARM objdump:

``` {.bash language="bash"}
arm-none-eabi-objdump -marm -Mforce-thumb -b binary -D --adjust-vma=0x1000 fw_all.bin > disasm_0x1000.txt
```

And this disassembly showed the expected "Clear register pattern":

``` {.[x86masm]Assembler language="[x86masm]Assembler"}
00001000 <.data>:
    1000:   2000        movs    r0, #0
    1002:   2100        movs    r1, #0
    1004:   2200        movs    r2, #0
    1006:   2300        movs    r3, #0
    1008:   2400        movs    r4, #0
```

So I knew my BIN file actually matched this documentation. That's when I
read the checksum calculation: "Start with byte value 0. Add each
firmware byte sequentially from offset 0, except the last. If file
length isn't a multiple of 256, add byte value 255 for missing bytes.
Add the checksum byte. Result should be 0."

Much simpler than private key signatures! I added checksum patching to
my RGN tool and successfully modified various format specifiers and
strings:


![image](https://github.com/jack898/rgntool/raw/main/imgs/versionChange.JPG)

_Version string displaying huge version numbers_


![image](https://github.com/jack898/rgntool/raw/main/imgs/strChange.JPG)

_Modified interface text strings_


![image](https://github.com/jack898/rgntool/raw/main/imgs/formatSpecifierChange.JPG)

_Format specifiers changed from `%u` to `%p` for hex display_


Getting overconfident, I tried changing some of the XML values like Unit
ID and model number... and bricked the watch.

# Conclusion

Modifying Garmin Forerunner 35 firmware is surprisingly easy due to its
simple checksum mechanism. This applies to most Garmin devices using RGN
format (versus newer GCD format)---many older devices and some modern
maritime ones use RGN.


**Warning:** The firmware binary is complex and contains data in various
different formats and levels of compression. Unless you understand
exactly what a section does, **only modify strings whose uses you can
isolate**. You can easily brick your device, rendering it unusable and
unrestorable.


If you do modify strings, be sure to keep the overall file length the
same. You can pad with NULL bytes as necessary. To avoid bricking the
device, if you are just hoping to modify strings, the LNG file method is
probably best.

# RGNTool Usage

If you read the disclaimer and still want to try modifying your Garmin
device's firmware, here's how you can use RGNTool to help:

1.  Make a copy of the RGN file (These can be found by Googling your
    device RGN files, or see the link to GMapTools in Acknowledgements)

2.  Run the parse command to find the start/end offsets for the firmware
    record

3.  Modify the desired portion of that record with a hex editor. You
    should also change an easy-to-find string so that you can confirm
    the firmware was actually patched (if the checksum is somehow
    incorrect, it may appear to install the update but not actually do
    so)

4.  Run the checksum command with the same start/end offsets. It will
    prompt you to change the checksum, type Y to do so

5.  Plug in your Garmin device and drop the modified RGN file into the
    main directory. Rename it GUPDATE.rgn

6.  Unplug the Garmin device and Install the update when prompted. Your
    device will restart and the changes should be applied!

This was an excellent learning experience about proprietary file
formats. Special thanks to Herbert Oppmann for his invaluable
documentation---check out [his
website](https://www.memotech.franken.de/FileFormats/) for more file
format analysis.

If you have an older Garmin device to experiment with, my RGN Tool can
help!

# Acknowledgements

- [**Garmin RGN Firmware Update File
  Format**](https://www.memotech.franken.de/FileFormats/Garmin_RGN_Format.pdf)
  & [**Garmin BIN Firmware File
  Format**](https://www.memotech.franken.de/FileFormats/Garmin_BIN_Format.pdf):
  Herbert Oppmann's file format analyses

- [**Pimp my
  Garmin**](https://blog.mbirth.uk/2022/08/07/pimp-my-garmin-turning-your-fenix-5-plus-into-a-d2-delta-pilot-watch.html):
  Blog post that led me to the BIN format analysis, and gave me some
  interesting ideas.

- [**GMapTools**](https://www.gmaptool.eu/en/content/forerunner): Source
  for sample RGN firmware files. I used Forerunner35_360.rgn in this
  guide.

- [**RGN GitHub repo**](https://github.com/x86driver/rgn/tree/master):
  Old C code base with an RGN parsing tool and what seems to be actual
  (leaked?) Garmin source code.


**Disclaimer:** This guide is provided for educational and research
purposes only. The author is completely unaffiliated with Garmin Ltd. or
any of its subsidiaries. Modifying device firmware may void your
warranty, brick your device, or cause other unintended consequences. The
author assumes no responsibility for any damage, loss of functionality,
or other issues that may result from following this guide. Proceed at
your own risk.
