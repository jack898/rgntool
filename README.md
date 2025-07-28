# RGNTool
Contains a parser, checksum calculator, and extraction tool to make it easier to understand and modify firmware on older Garmin models (any Garmin using the RGN update format).

If you're unfamiliar with the RGN format or Garmin hacking, I highly recommend you review the file format documentation in Acknowledgements and my guide [Hacking Older Garmins](https://github.com/jack898/rgntool/blob/main/HackingOlderGarmins.pdf).

# Installation
No dependencies required beyond Python >= 3.2. Just download rgntool.py and see the sections below for how to use your desired tool.

RGN firmware files for various Garmin devices can be found on [GMapTool](https://www.gmaptool.eu/en/content/sports).

## Parser
Analyzes RGN files, extracting any relevant information. This includes:
- Each record and its offset, size, and type
- Any known information within the record; this includes region IDs/purposes, version info, build info, etc.

#### Usage
```
python rgnparser.py parse <filename.rgn>
```

## Extractor
Extracts a record (or any desired section) from an RGN file to an external file, based on provided offsets. Includes bytes at start/end offsets.

#### Usage
```
python rgnparser.py extract <filename.rgn> <start_offset> <end_offset> <output.bin>
```

## Checksum Calculator
Calculates the checksum for firmware record in an RGN file, based on provided offsets. Checks if current checksum is valid, and updates to valid checksum if desired.

#### Usage
```
python rgnparser.py checksum <filename.rgn> <start_offset> <end_offset>
```

# Acknowledgements
[Garmin RGN Firmware Update File Format](https://www.memotech.franken.de/FileFormats/Garmin_RGN_Format.pdf) and [Garmin BIN Firmware File Format](https://www.memotech.franken.de/FileFormats/Garmin_BIN_Format.pdf): Analyses of the Garmin update and firmware file formats.

[RGN](https://github.com/x86driver/rgn/tree/master): Old repo containing some C code to parse RGN files. I largely based the parsing tool off of this, adding some features and fixing some bugs.

# Disclaimer
This tool is provided for educational and research purposes only.
I am not affiliated with Garmin Ltd. or any of its subsidiaries.
Use of this tool is at your own risk.

Modifying or parsing firmware files (such as .RGN) may lead to permanent damage ("bricking") of your device.
I assume no responsibility or liability for any loss, damage, or consequences resulting from the use or misuse of this tool.

By using this tool, you acknowledge and agree to these terms.

