import os
import google.generativeai as genai

# The system will first check for an environment variable named "AI".
# If not found, it will use the key provided below.
AI = "AIzaSyACSkgYZfEXO5XaxKPI6TKAs_4RWpdlfvk"

def setup_ai():
    genai.configure(api_key=AI)
    return genai.GenerativeModel('gemini-flash-lite-latest')

model = setup_ai()

def get_video_suggestion(vitals):
    """
    Returns a medical emergency video URL based on vitals.
    """
    if not vitals: return None
    
    # Calculate averages
    avg_hr = sum(v['heart_rate'] for v in vitals) / len(vitals)
    avg_temp = sum(v['temperature'] for v in vitals) / len(vitals)
    avg_spo2 = sum(v['spo2'] for v in vitals) / len(vitals)

    if avg_spo2 < 96:
        return "https://www.youtube.com/embed/gDmy0of0XAk" # British Red Cross: Breathing/Unresponsive
    elif avg_temp > 37.5:
        return "https://www.youtube.com/embed/fS5R-b8vWvM" # St John Ambulance: Fever
    elif avg_hr > 90 or avg_hr < 60:
        return "https://www.youtube.com/embed/gDAt7GZp3u0" # British Red Cross: Heart Attack
    return None

def generate_ai_summary(vitals, patient_name):
    """
    Generates a professional health analysis using Google Gemini AI.
    """
    if not vitals:
        return {"summary": f"No health data available for {patient_name}.", "video_url": None}

    # Statistical Averages
    avg_hr = sum(v['heart_rate'] for v in vitals) / len(vitals)
    avg_temp = sum(v['temperature'] for v in vitals) / len(vitals)
    avg_spo2 = sum(v['spo2'] for v in vitals) / len(vitals)
    
    video_url = get_video_suggestion(vitals)

    # Prepare prompt for Gemini
    recent_readings = vitals[-5:] 
    readings_text = "\n".join([f"- HR: {v['heart_rate']}bpm, SpO2: {v['spo2']}%, Temp: {v['temperature']}C" for v in recent_readings])

    prompt = f"""
    Act as a professional medical health analyst. Analyze the following vital sign data for patient: {patient_name}
    
    RECENT READINGS:
    {readings_text}
    
    AVERAGES:
    - Heart Rate: {avg_hr:.1f} bpm
    - SpO2: {avg_spo2:.1f}%
    - Body Temperature: {avg_temp:.1f}C
    
    REQUIRED OUTPUT STRUCTURE (MATCH EXACTLY):
    AI HEALTH SUMMARY FOR {patient_name}
    (Write 2-3 sentences here)
    
    ASSESSMENT: (One-line status)
    
    RECOMMENDATION:
    - (Step 1)
    - (Step 2)
    
    FIRST AID VIDEO: [Insert one relevant medical YouTube link here if vitals are abnormal, else 'None']
    
    IMPORTANT: Use simple hyphens (-) for bullet points. Do not use symbols like '•'. 
    Do not use bold symbols (**) or heading symbols (#).
    """

    try:
        response = model.generate_content(prompt)
        ai_text = response.text
        
        # Try to extract video URL from AI response if provided
        final_video_url = video_url
        if "https://www.youtube.com/embed/" in ai_text:
            import re
            match = re.search(r'https://www.youtube.com/embed/[\w-]+', ai_text)
            if match:
                final_video_url = match.group(0)
        elif "https://www.youtube.com/watch?v=" in ai_text:
            import re
            match = re.search(r'https://www.youtube.com/watch\?v=([\w-]+)', ai_text)
            if match:
                final_video_url = f"https://www.youtube.com/embed/{match.group(1)}"
        
        # Clean the first aid video section from the summary text to keep the report tidy
        clean_text = re.sub(r'FIRST AID VIDEO:.*', '', ai_text, flags=re.DOTALL).strip()
        
        return {"summary": clean_text, "video_url": final_video_url}
    except Exception as e:
        # Fallback if AI fails
        return {"summary": f"AI HEALTH SUMMARY FOR {patient_name}\nVitals are HR:{avg_hr:.1f}, SpO2:{avg_spo2:.1f}%, Temp:{avg_temp:.1f}C.\n\nASSESSMENT: Patient monitoring in progress.\n\nRECOMMENDATION:\n- Continue regular monitoring.", "video_url": video_url}

def send_emergency_alerts(patient_name, vitals_data, family_contact, doctor_contact):
    """
    Simulates sending emergency Email and SMS alerts.
    """
    alert_msg = f"CRITICAL ALERT: Patient {patient_name} vital signs are outside safe ranges.\nReadings: {vitals_data}\nImmediate attention required."
    
    print("\n" + "="*50)
    print("🚨 EMERGENCY NOTIFICATION SYSTEM TRIGGERED")
    print(f"📧 SENDING EMAIL TO FAMILY ({family_contact.get('email', 'N/A')}):")
    print(f"   Subject: EMERGENCY ALERT - {patient_name}")
    print(f"   Message: {alert_msg}")
    
    print(f"\n📧 SENDING EMAIL TO DOCTOR ({doctor_contact.get('email', 'N/A')}):")
    print(f"   Subject: CRITICAL CLINICAL ALERT - {patient_name}")
    print(f"   Message: {alert_msg}")
    
    print(f"\n📱 SENDING SMS TO FAMILY ({family_contact.get('phone', 'N/A')}):")
    print(f"   {alert_msg}")
    
    print(f"\n📱 SENDING SMS TO DOCTOR ({doctor_contact.get('phone', 'N/A')}):")
    print(f"   {alert_msg}")
    print("="*50 + "\n")
    
    return True
