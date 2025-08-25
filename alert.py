import json
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import geoip2.database
from ipaddress import ip_address
import folium
import os

# ---------- CONFIGURATION ----------
COWRIE_LOG = "your file path where you save the logs"
GEOIP_DB = "/home/dark/cowrie/GeoLite2-City.mmdb"  # Download from MaxMind
EMAIL_FROM = "your gmail id"
EMAIL_TO = "your gmail id"
EMAIL_PASSWORD = "app password"
DAILY_REPORT_PATH = "/home/dark/cowrie/daily_report.html"

# ---------- EMAIL ALERT FUNCTION ----------
# Added password argument
def send_alert(ip, status, username="", password="", city="unknown", country="unknown"):
    subject = f"Cowrie Alert: {status} login"
    # Added password in body
    body = f"SSH {status} detected from IP: {ip}\nUsername: {username}\npassword: {password}\nLocation: {city}, {country}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"[ALERT SENT] {status} login from {ip} ({city}, {country})")
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")

# ---------- GEOLOCATION FUNCTION ----------
def get_geo(ip, reader):
    try:
        response = reader.city(ip)
        lat = response.location.latitude
        lon = response.location.longitude
        city  = response.city.name if response.city.name else "unknown"
        country = response.country.name if response.country.name else "unknown"
        return lat, lon, city, country
    except Exception:
        return None, None, "Unknown", "Unknown"

#-----------CHECK PUBLIC IP --------------
def is_puplic_ip(ip):
    try:
        return ip_address(ip).is_global
    
    except:
          return False

# ---------- LOG MONITOR FUNCTION ----------
def tail_f(file):
    file.seek(0, 2)  # Move to end of file
    while True:
        line = file.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

# ---------- DAILY REPORT FUNCTION ----------
def generate_report(attacks):
    map_center = [20, 0]  # Default world map center
    attack_map = folium.Map(location=map_center, zoom_start=2)
    
    for attack in attacks:
        lat, lon = attack['lat'], attack['lon']
        ip = attack['ip']
        city = attack['city']
        country = attack['country']
        if lat and lon:
            folium.Marker([lat, lon], popup=f"{ip} - {city}, {country}").add_to(attack_map)
    
    attack_map.save(DAILY_REPORT_PATH)
    print(f"[REPORT GENERATED] {DAILY_REPORT_PATH}")

# ---------- MAIN FUNCTION ----------
def main():
    reader = geoip2.database.Reader(GEOIP_DB)
    attacks_today = []
    last_day = datetime.now().day

    with open(COWRIE_LOG) as f:
        for line in tail_f(f):
            try:
                event = json.loads(line)
                eventid = event.get('eventid')
                ip = event.get('src_ip')
                username = event.get('username', "")
                password = event.get('password', "")  #FIX: Added password field

                lat, lon, city, country = get_geo(ip, reader)
                 
                # Detect login attempts
                if eventid == 'cowrie.login.failed':
                    print(f"[FAILED LOGIN] {ip} | {username} | {password}")  # Added password in print
                    send_alert(ip, 'FAILED', username, password, city, country) # Pass password
                elif eventid == 'cowrie.login.success':
                    print(f"[SUCCESS LOGIN] {ip} | {username} | {password}")   # Added password in print
                    send_alert(ip, 'SUCCESS', username, password, city, country)  # Pass password

                # Store for daily report
                lat, lon, city, country = get_geo(ip, reader)
                attacks_today.append({'ip': ip, 'lat': lat, 'lon': lon, 'city': city, 'country': country})

                # Generate daily report at midnight
                current_day = datetime.now().day
                if current_day != last_day:
                    generate_report(attacks_today)
                    attacks_today = []
                    last_day = current_day

            except Exception as e:
                print(f"[ERROR] {e}")
 
  # FIX: Corrected the __name__check               

if __name__ == "__main__":
    main()
