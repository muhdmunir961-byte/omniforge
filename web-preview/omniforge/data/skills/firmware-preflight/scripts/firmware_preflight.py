import argparse,json,shutil,subprocess,sys

def main():
 p=argparse.ArgumentParser(description='Non-invasive ESP32 tooling preflight');p.parse_args()
 out={'python':sys.version.split()[0],'executables':{n:shutil.which(n) for n in ['pio','arduino-cli','esptool','idf.py']}}
 try:
  from serial.tools import list_ports
  out['serial_ports']=[{'device':x.device,'description':x.description} for x in list_ports.comports()]
 except ImportError:out['serial_ports']='pyserial not installed (optional)'
 print(json.dumps(out,indent=2))
if __name__=='__main__':main()
