# RGNTool
# 
# Comprehensive tool for working with Garmin RGN firmware files
# Usage: 
#   python rgntool.py [parse/checksum/extract] <rgn_file> [start_offset_hex] [end_offset_hex] [output_file_name]

import struct
import sys
import argparse

# Defining record types and known region IDs
DATA_VERSION_TYPE = b'D'
APP_VERSION_TYPE = b'A'
REGION_TYPE = b'R'
REGION_IDS = {
    0: "Amongst others, RGN file",
    1: "Identified but purpose unknown",
    2: "Identified but purpose unknown",
    3: "IMG file",
    5: "Identified but purpose unknown",
    10: "dskimg.bin (IMG file format)",
    12: "boot.bin",
    14: "fw_all.bin (In DeltaSmart_350.rgn, the content is again a RGN file which contains the actual firmware in its region 14.)",
    16: "logo.bin",
    17: "Voice (IMG file format or other)",
    78: "ZIP, IMG or RGN file",
    80: "Identified but purpose unknown",
    81: "Identified but purpose unknown",
    82: "Identified but purpose unknown",
    85: "fw_all2.bin",
    86: "Texts (e.g. in Text_ApproachS40_Chinese_260.rgn)",
    93: "gmaptz.img (Timezone, IMG file format)",
    97: "Speech recognition data (ASR or SRD)",
    132: "Identified but purpose unknown Always starts with the six bytes 04 00 00 0C 00 00, optionally followed by another 4 bytes (different content)",
    146: "SQLite format 3, DTF = DIdentified but purpose unknown Toll Fees",
    148: "SQLite format 3, DTF = DIdentified but purpose unknown Toll Fees",
    162: "Identified but purpose unknown",
    245: "GCD or RGN firmware update file",
    246: "Identified but purpose unknown",
    247: "Identified but purpose unknown",
    248: "Identified but purpose unknown",
    249: "Display firmware",
    250: "Identified but purpose unknown",
    251: "WiFi firmware, GCD firmware update file",
    252: "Identified but purpose unknown",
    253: "GCD firmware update file",
    255: "pk_text.zip (ZIP file with help texts), GCD firmware update file, or XML file"
}

# ============================================================================
# RGN PARSING FUNCTIONS
# ============================================================================

# read_cstr
# Purpose: Read a C-string from bytes
# Returns: C-string as ASCII text
def read_cstr(data, start):
    end = data.find(b'\x00', start)
    if end == -1:
        return "", start
    return data[start:end].decode('ascii', errors='replace'), end + 1

# parse_vir_header
# Purpose: Extracts file ID and version from Version Identification Record section
# Returns: Next byte after VIR header
def parse_vir_header(data, offset):
    file_id, version = struct.unpack_from("<I H", data, offset)

    # Get file ID as ASCII string from bytes
    file_id, _ = read_cstr(data, offset)
    print("")
    print(f"Total Size: 6 bytes, Type: Version Identification Record")
    print(f"Record Data Start: 0x00000000")
    print(f"Record Data Start: 0x00000005")
    print(f"-- RECORD DATA --")
    print(f"File ID: {file_id[:4]}")
    print(f"Format Version: {version // 100}.{version % 100:02d}")
    print("")
    return offset + 6 # Skip over char[4] (file_id) + ushort (format version) 

# parse_advr
# Purpose: Extracts data version from data version record
# Returns: Next byte after version
def parse_advr(data, offset, size):
    if size != 2: 
        print("Incorrect size for data version record")
        return offset
    
    version, = struct.unpack_from("<H", data, offset)

    print(f"Record Data Start: 0x{offset:08X}")
    print(f"Record Data End: 0x{offset+size-1:08X}")
    
    print(f"-- RECORD DATA --")
    print(f"Data version: {version // 100}.{version % 100:02d}")

    return offset + 2 # Skip over ushort (data version) = 2 bytes

# parse_avr
# Purpose: Extracts version, builder, buildDate, and buildTime from application version record 
# Returns: Offset plus 2 bytes
def parse_avr(data, offset, size):
    if size < 2: # Catch malformed data
        print("Not enough data for full application version record")
        return offset

    version, = struct.unpack_from("<H", data, offset)
    print(f"Record Data Start: 0x{offset:08X}")
    print(f"Record Data End: 0x{offset+size-1:08X}")
    offset += 2 # Skip over ushort (application version)

    # Get Builder/buildDate/buildTime as ASCII strings from bytes
    builder, offset = read_cstr(data, offset)
    build_date, offset = read_cstr(data, offset)
    build_time, offset = read_cstr(data, offset)

    print(f"-- RECORD DATA --")
    print(f"Application Version: {version // 100}.{version % 100:02d}")
    print(f"Builder: {builder}")
    print(f"Date: {build_date}")
    print(f"Time: {build_time}")

    return offset

# parse_region
# Purpose: Extracts region ID, delay, region data size, start/end address, and first 16 bytes from region records
# Returns: Next byte after region record
def parse_region(data, offset, size):
    if size < 10: # Catch malformed data and return
        print("Not enough data for region header")
        return offset 
    
    region_id, delay, region_size = struct.unpack_from("<HII", data, offset)
    offset += 10 # Skip over ushort (region ID) + uint (delay) + uint (size) = 10 bytes
    
    print(f"Record Data Size: {region_size} bytes")
    # Give start/end offsets as 8-bit hex addresses
    print(f"Record Data Start: 0x{offset:08X}")
    print(f"Record Data End: 0x{offset+region_size-1:08X}")

    print(f"-- RECORD DATA --")
    print(f"Region ID: {region_id}")
    print(f"    * Purpose: {REGION_IDS[region_id] if region_id in REGION_IDS else 'Unidentified'}")
    print(f"Delay: {delay} ms")
    # Display first 16 bytes as hex
    preview = data[offset:offset+16]
    print("Contents (first 16 bytes):", ' '.join(f"{b:02X}" for b in preview))
    return offset + region_size

# parse_data_record
# Purpose: Identifies each record type and passes to with appropriate helper
# Returns: Next byte after record
def parse_data_record(data, offset):
    print(f"----------------------------\n")
    if offset + 5 > len(data): # Catch malformed data
        print("Incomplete data record header")
        return offset, False

    size, rec_type = struct.unpack_from("<I c", data, offset)
    print(f"Total Size: {size} bytes, Type: {rec_type.decode('ascii', errors='replace')}", end=' ')
    offset += 5 # Skip over uint (total size) + char (type) = 5 bytes

    payload_offset = offset
    # Choose appropriate parsing function based on record type
    if rec_type == DATA_VERSION_TYPE:
        print("(DATA_VERSION_TYPE)")
        offset = parse_advr(data, payload_offset, size)
    elif rec_type == APP_VERSION_TYPE:
        print("(APP_VERSION_TYPE)")
        offset = parse_avr(data, payload_offset, size)
    elif rec_type == REGION_TYPE:
        print("(REGION_TYPE)")
        offset = parse_region(data, payload_offset, size)
    else:
        print("(Unknown type)")
        offset += size

    print("")
    return offset, True

# handle_rgn_data
# Purpose: Steps through each record, handling them according to their type
# Returns: None
def handle_rgn_data(data):
    # Handle Version Identification Record
    offset = 0
    offset = parse_vir_header(data, offset)

    # Handle the list of Records
    record_count = 0
    while offset < len(data):
        offset, ok = parse_data_record(data, offset)
        if not ok:
            break
        record_count += 1

    print(f"\nParsed {record_count} data record(s).")

# ============================================================================
# CHECKSUM CALCULATION FUNCTIONS
# ============================================================================

# calc_checksum
# Purpose: Calculates checksum byte for firmware
# Returns: Checksum byte value, total firmware data length, and necessary padding
def calc_checksum(data, start_offset, firmware_end_offset):
    firmware_data = data[start_offset:firmware_end_offset + 1] # Get entire bin

    # If total bytes isn't multiple of 256, need to pad
    pad_needed = (256 - (len(firmware_data)+1 % 256)) % 256
    padded_firmware = firmware_data + bytes([0xFF] * pad_needed)

    # Add up all bytes, including padding if necessary. all bytes + checksum should equal 0.
    sum_without_checksum = sum(padded_firmware)
    required_checksum = (-sum_without_checksum) % 256
    return required_checksum, len(firmware_data), pad_needed

# compute_checksum_info
# Purpose: Gets checksum byte and compares to current checksum byte
# Returns: None
def compute_checksum_info(file_path, start_offset, checksum_byte_offset):
    with open(file_path, "rb") as f:
        data = f.read()

    if checksum_byte_offset >= len(data): # Catch malformed file
        raise ValueError("Checksum byte offset is beyond file size.")

    actual_checksum = data[checksum_byte_offset] # Get current checksum (final byte)

    # Get new checksum, using all of bin minus checksum byte
    required_checksum, fw_len, padding = calc_checksum(data, start_offset, checksum_byte_offset - 1)

    print(f"Firmware data length: {fw_len}")
    print(f"Padding added: {padding} (0xFF)")
    print(f"Actual checksum byte at 0x{checksum_byte_offset:X}: 0x{actual_checksum:02X}")
    print(f"Required checksum byte: 0x{required_checksum:02X}")

    if actual_checksum == required_checksum:
        print("\nChecksum is correct.")
    else:
        print("\nChecksum is incorrect.")
        print("Want to update the checksum to the correct value? (Y/N)")
        # Get user input to update checksum
        if input().strip().upper() == 'Y':
            # Update checksum byte in the file
            data = bytearray(data)
            data[checksum_byte_offset] = required_checksum
            with open(file_path, "wb") as f:
                f.write(data)
            print("Checksum updated.")
        else:
            print("Checksum not updated.")


# ============================================================================
# EXTRACT/MODIFY FUNCTIONS
# ============================================================================

# extract_region
# Purpose: Extract record from RGN file based on start and end offsets
# Returns: None, writes to file
def extract_record(rgn_file_path, start_offset, end_offset, output_file_path):
    try:
        with open(rgn_file_path, "rb") as f:
            data = f.read()
        
        # Validate offsets
        if start_offset >= len(data):
            raise ValueError(f"Start offset 0x{start_offset:X} is beyond file size ({len(data)} bytes)")
        if end_offset >= len(data):
            raise ValueError(f"End offset 0x{end_offset:X} is beyond file size ({len(data)} bytes)")
        if start_offset > end_offset:
            raise ValueError(f"Start offset (0x{start_offset:X}) cannot be greater than end offset (0x{end_offset:X})")
        
        # Extract the record data, inclusive
        region_data = data[start_offset:end_offset + 1]
        region_size = len(region_data)
        
        # Write extracted data to output file
        with open(output_file_path, "wb") as f:
            f.write(region_data)
        
        print(f"Successfully extracted record:")
        print(f"  Source: {rgn_file_path}")
        print(f"  Start offset: 0x{start_offset:08X}")
        print(f"  End offset: 0x{end_offset:08X}")
        print(f"  Record size: {region_size} bytes")
        print(f"  Output file: {output_file_path}")
        
    except FileNotFoundError:
        raise FileNotFoundError(f"RGN file '{rgn_file_path}' not found")
    except Exception as e:
        raise Exception(f"Error extracting record: {e}")

# ============================================================================
# MAIN FUNCTION AND CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="RGNTool - Interpret and modify Garmin firmware",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        Parse an RGN file:
            python rgntool.py parse firmware.rgn
            
        Calculate checksum for firmware binary:
            python rgntool.py checksum fw_all.bin 0x804B 0x8704A
            
        Extract fw_all.bin from RGN file:
            python rgntool.py extract firmware.rgn 0x1000 0x7FFFF fw_all.bin
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse an RGN file')
    parse_parser.add_argument('rgn_file', help='Path to the RGN file to parse')
    
    # Checksum command
    checksum_parser = subparsers.add_parser('checksum', help='Calculate and verify firmware checksum')
    checksum_parser.add_argument('firmware_file', help='Path to the firmware binary file (e.g., fw_all.bin)')
    checksum_parser.add_argument('start_offset', help='Start offset of the record in hex (e.g., 0x1000)')
    checksum_parser.add_argument('checksum_byte_offset', help='Checksum byte offset in hex (e.g., 0x7EEFF). Should be the last byte of the record.')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract a record from an RGN file')
    extract_parser.add_argument('rgn_file', help='Path to the source RGN file')
    extract_parser.add_argument('start_offset', help='Start offset of the record in hex (e.g., 0x1000)')
    extract_parser.add_argument('end_offset', help='End offset of the record in hex (e.g., 0x7FFFF)')
    extract_parser.add_argument('output_file', help='Path for the extracted record file (e.g., fw_all.bin)')

    args = parser.parse_args()
    
    if args.command == 'parse':
        try:
            with open(args.rgn_file, "rb") as f:
                file_data = f.read()
            print(f"Parsing RGN file: {args.rgn_file}")
            handle_rgn_data(file_data)
        except FileNotFoundError:
            print(f"Error: File '{args.rgn_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error parsing RGN file: {e}")
            sys.exit(1)
            
    elif args.command == 'checksum':
        try:
            start_offset = int(args.start_offset, 16)
            cs_offset = int(args.checksum_byte_offset, 16)
            print(f"Calculating checksum for: {args.firmware_file}")
            compute_checksum_info(args.firmware_file, start_offset, cs_offset)
        except ValueError as e:
            print(f"Error: Invalid hex offset - {e}")
            sys.exit(1)
        except FileNotFoundError:
            print(f"Error: File '{args.firmware_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error calculating checksum: {e}")
            sys.exit(1)
            
    elif args.command == 'extract':
        try:
            start_offset = int(args.start_offset, 16)
            end_offset = int(args.end_offset, 16)
            extract_record(args.rgn_file, start_offset, end_offset, args.output_file)
        except ValueError as e:
            print(f"Error: Invalid hex offset - {e}")
            sys.exit(1)
        except FileNotFoundError:
            print(f"Error: File '{args.rgn_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error extracting region: {e}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()