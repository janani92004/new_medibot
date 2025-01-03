import streamlit as st
import pandas as pd
import urllib.parse
import requests
import google.generativeai as genai
import ast
from streamlit_geolocation import streamlit_geolocation 
import time
from googleapiclient.discovery import build
from streamlit_option_menu import option_menu

# Access the Google API key from the secrets
yt_api_key =st.secrets["api_keys"]['yt_api_key']
api_key =st.secrets["api_keys"]['api_key']
API_KEY_2 = st.secrets["api_keys"]['API_KEY_2']
API_KEY_3 = st.secrets["api_keys"]['API_KEY_3']

# Configure the API with the key
genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-pro')

# Load datasets
dataset1_path = 'medical_records.csv'
dataset2_path = 'dosage_records.csv'
first_aid_dataset_path = 'first_aid.csv'

dataset1 = pd.read_csv(dataset1_path)
dataset2 = pd.read_csv(dataset2_path, encoding='latin-1')
first_aid_dataset = pd.read_csv(first_aid_dataset_path, encoding='latin-1')

# Initialize global DataFrames
df_first_aid = pd.DataFrame(columns=['Date', 'Time', 'Emergency'])
df_diagnosis = pd.DataFrame(columns=['Date', 'Time', 'Name', 'Age', 'Diagnosis', 'Recommendation'])

# At the start of your file, after imports
st.set_page_config(layout="wide")  # Makes the page use full width

# Update the title styling
st.markdown("""
    <h1 style='text-align: left;'>Medi-bot: Your Personal Medical Chat-bot</h1>
    """, unsafe_allow_html=True)

# Wrap main content in columns for better spacing
col1, col2, col3 = st.columns([3,1,1])  # Makes the first column wider

# At the start of your main code, add these session state initializations
if 'current_task' not in st.session_state:
    st.session_state.current_task = None
if 'show_hospitals' not in st.session_state:
    st.session_state.show_hospitals = False
if 'show_medical_shops' not in st.session_state:
    st.session_state.show_medical_shops = False

with col1:  # Put main content in left column
    # User choice
    user_choice = option_menu(
    menu_title="Main Menu",  # Title of the menu
    options=["💊 First Aid", "🩹 Diagnosis and Medicine Recommendation", "🏥 Search Hospitals", "💉 Search Medical Shops"],  # Updated Menu options
    icons=["🩹", "💊", "🏥", "💉"],  # Emojis for the menu items
    menu_icon="🏥",  # Icon for the entire menu (you can also use an emoji here)
    default_index=0,  # Default selected option
)


    # Clear previous results when task changes
    if 'previous_task' not in st.session_state:
        st.session_state.previous_task = user_choice
    if st.session_state.previous_task != user_choice:
        st.session_state.show_hospitals = False
        st.session_state.show_medical_shops = False
        st.session_state.previous_task = user_choice

    # Function to provide emergency advice
    def provide_emergency_advice(user_emergency, dataset):
        for _, row in dataset.iterrows():
            if pd.notna(row['Emergency']):
                if any(keyword in user_emergency.lower() for keyword in row['Emergency'].lower().split()):
                    return row.to_dict()  # Convert the row to a dictionary
        return None
    
    def search_youtube_for_remedies(symptoms, api_key):
        
        # Format the query for YouTube search
        query = f"home remedies for {' '.join(symptoms.split(','))}"

        # Build the YouTube API client
        youtube = build('youtube', 'v3', developerKey=api_key)

        # Perform the search
        try:
            search_response = youtube.search().list(
                q=query,
                part='snippet',
                type='video',
                maxResults=1  # Fetch only the first result
            ).execute()

            # Extract video information
            if search_response['items']:
                video = search_response['items'][0]
                video_title = video['snippet']['title']
                video_id = video['id']['videoId']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                return video_title, video_url
            else:
                return None, None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None, None

    # Function to recommend drug
    def recommend_drug(symptoms, age, dataset1, dataset2):
        symptoms_list = [symptom.strip().lower() for symptom in symptoms.split(',')]
        disease = None
        matched_row = None

        # Custom logic for specific symptom combinations
        if set(['fever', 'headache', 'fatigue']).issubset(symptoms_list):
            disease = 'Sinusitis'
        elif 'headache' in symptoms_list and len(symptoms_list) == 1:
            disease = ' Possible Migraine'
        elif set(['fever', 'cough', 'fatigue']).issubset(symptoms_list):
            disease = 'Common Cold'
        elif set(['fever', 'sore throat', 'fatigue']).issubset(symptoms_list):
            disease = 'Throat Infection'
        elif set(['fever', 'nausea', 'fatigue']).issubset(symptoms_list):
            disease = 'Stomach Infection'
        else:
            for index, row in dataset1.iterrows():
                if any(symptom in row['Symptoms'].lower() for symptom in symptoms_list):
                    disease = row['Preliminary_Disease_Diagnosis']
                    matched_row = row
                    break

        if matched_row is not None or disease:
            if matched_row is None:
                for index, row in dataset1.iterrows():
                    if row['Preliminary_Disease_Diagnosis'].lower() == disease.lower():
                        matched_row = row
                        break

            recommended_medicine = matched_row['Recommended_Medicine']
            recommended_dosage = None

            for index, row in dataset2.iterrows():
                if row['Preliminary_Disease_Diagnosis'].lower() == disease.lower():
                    if age <= 12:
                        st.info('⚠️Please visit a doctor or your local pediatrician for children')
                    elif age > 12 and age <= 65:
                        recommended_dosage = row['Adult']
                    else:
                        recommended_dosage = row['Adult']
                    break

            if recommended_dosage is not None:
                st.info('⚠️Please visit a doctor if conditions worsen within a day.')
                return {
                    'Diagnosis': disease,
                    'Medicine': recommended_medicine,
                    'Dosage': recommended_dosage,
                    'Advice': matched_row['Recommended_Advice']
                }
        return None

    def search_youtube_emergency(emergency, api_key):
    # Build the search prompt
        query = f"how to perform first aid for a: {emergency} in english"
        
        # Build the YouTube API client
        youtube = build('youtube', 'v3', developerKey=api_key)

        # Perform the search
        search_response = youtube.search().list(
            q=query,
            part='snippet',
            type='video',
            maxResults=1  # Fetch only the first result
        ).execute()

        # Extract the video information
        if search_response['items']:
            video = search_response['items'][0]
            video_title = video['snippet']['title']
            video_id = video['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            return video_title, video_url
        else:
            return None, None


    def search_and_format_hospitals():
    # Get the user's location (latitude and longitude) using streamlit_geolocation
        location = streamlit_geolocation()
        st.write('Please click the above button to find your location')
        time.sleep(10)  # This function should return latitude and longitude
        
        if location:
            latitude = location['latitude']
            longitude = location['longitude']
            
            st.write(f"Latitude: {latitude}, Longitude: {longitude}")
            
            # Google Places API endpoint and API key
            
            places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            
            # Parameters for the API call
            params = {
                'location': f'{latitude},{longitude}',
                'radius': 1000,  # 1 km radius
                'type': 'hospital',  # Change this to 'hospital' for hospitals
                'key': API_KEY_2
            }

            try:
                response = requests.get(places_url, params=params)
                data = response.json()


                if data.get('status') != 'OK':
                    st.error(f"Failed to retrieve data. API Status: {data.get('status')}")
                    return None

                raw_hospitals = []
                for place in data.get('results', [])[:5]:
                    name = place.get('name', 'N/A')
                    address = place.get('vicinity', 'N/A')
                    place_id = place.get('place_id', '')
                    phone_number = 'N/A'

                    encoded_name = urllib.parse.quote(name)
                    directions_link = f"https://www.google.com/maps/search/?api=1&query={encoded_name}"

                    if place_id:
                        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                        details_params = {
                            'place_id': place_id,
                            'key': API_KEY_2
                        }
                        details_response = requests.get(details_url, params=details_params)
                        details_data = details_response.json()
                        if details_data.get('status') == 'OK':
                            phone_number = details_data.get('result', {}).get('formatted_phone_number', 'N/A')

                    raw_hospitals.append({
                        "name": name,
                        "address": address,
                        "phone": phone_number,
                        "directions": directions_link
                    })

                if not raw_hospitals:
                    st.error("No hospitals found")
                    return None

                # Format data and create a structured output for Gemini
                hospitals_data = "Here are the hospitals found:\n\n"
                for idx, hospital in enumerate(raw_hospitals, 1):
                    hospitals_data += f"Hospital {idx}:\nName: {hospital['name']}\nAddress: {hospital['address']}\nPhone: {hospital['phone']}\nDirections: {hospital['directions']}\n\n"

                # Send the prompt to Gemini for parsing the raw data into a structured format
                prompt = f"""
                Parse these hospital details into a structured format. For each hospital, extract:
                1. Name
                2. Address (the part with the street name)
                3. Phone number (the 10-digit or landline number)
                4. Directions (Google Maps URL with the hospital name)

                Format as a list of dictionaries like this:
                [
                    {{
                        "name": "Hospital Name",
                        "address": "Street address",
                        "phone": "Phone number",
                        "directions": "https://www.google.com/maps/search/?api=1&query=Hospital+Name"
                    }}
                ]

                Here are the details to parse:
                {hospitals_data}

                Return ONLY the Python list, no other text.
                """


                # Assuming 'model' is your Gemini model instance
                response = model.generate_content(prompt)
                hospitals = ast.literal_eval(response.text)  # Convert the response text into a Python object

                return hospitals

            except Exception as e:
                st.error(f"Error fetching data: {e}")
                return None
        else:
            st.warning("Please click the 'Get My Location' button to allow geolocation access.")
            return None


    def create_emergency_sidebar():
        with st.sidebar:
            st.title("🚨 Emergency Contacts")
            
            # Read emergency contacts from CSV with latin-1 encoding
            emergency_df = pd.read_csv('Emergency_Services_Worldwide.csv', encoding='latin-1')
            
            # Get unique countries for selector
            countries = emergency_df['Country'].unique()
            
            # Country selector
            country = st.selectbox(
                "Select your country",
                countries
            )
            
            st.markdown("---")
            
            # Display contacts for selected country
            if country:
                # Filter contacts for selected country
                country_contacts = emergency_df[emergency_df['Country'] == country]
                
                # Display country name
                st.markdown(f"### {country}")
                
                # Display all emergency services for the country
                for _, row in country_contacts.iterrows():
                    st.markdown(f"- **{row['Service']}**: {row['Number']}")
            
            # Disclaimer
            st.markdown("---")
            st.caption("""
                ⚠️ **Disclaimer**: In case of emergency, immediately dial your 
                country's emergency services number.
            """)
            
            st.markdown("---")
            
            # Initialize session states if they don't exist
         

    def search_and_format_medical_shops():
    # Get the user's location (latitude and longitude) using streamlit_geolocation
        location = streamlit_geolocation()
        st.write('Please click the above button to find your location')
        time.sleep(10)  # This function should return latitude and longitude
        
        if location:
            latitude = location['latitude']
            longitude = location['longitude']
            
            st.write(f"Latitude: {latitude}, Longitude: {longitude}")
            
            # Google Places API endpoint and API key
            
            places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            
            # Parameters for the API call
            params = {
                'location': f'{latitude},{longitude}',
                'radius': 1000,  # 4 km radius
                'type': 'pharmacy',  # Change this to 'pharmacy' for medical shops
                'key': API_KEY_3
            }

            try:
                response = requests.get(places_url, params=params)
                data = response.json()
                
                # Debugging the API response
               

                if data.get('status') != 'OK':
                    st.error(f"Failed to retrieve data. API Status: {data.get('status')}")
                    return None

                raw_shops = []
                for place in data.get('results', [])[:5]:
                    name = place.get('name', 'N/A')
                    address = place.get('vicinity', 'N/A')
                    # Distance can be estimated from the search parameters, not available directly from the API response.
                    # You can calculate actual distance based on user's location if needed.

                    # Fetching phone number (if available)
                    place_id = place.get('place_id', '')
                    phone_number = 'N/A'

                    encoded_name = urllib.parse.quote(name)
                    directions_link = f"https://www.google.com/maps/search/?api=1&query={encoded_name}"

                    if place_id:
                        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                        details_params = {
                            'place_id': place_id,
                            'key': API_KEY_3
                        }
                        details_response = requests.get(details_url, params=details_params)
                        details_data = details_response.json()
                        if details_data.get('status') == 'OK':
                            phone_number = details_data.get('result', {}).get('formatted_phone_number', 'N/A')

                    raw_shops.append({
                        "name": name,
                        "address": address,
                        "phone": phone_number,
                        "directions": directions_link
                    })

                if not raw_shops:
                    st.error("No medical shops found")
                    return None

                # Format data and create a structured output for Gemini
                shops_data = "Here are the medical shops found:\n\n"
                for idx, shop in enumerate(raw_shops, 1):
                    shops_data += f"Shop {idx}:\nName: {shop['name']}\nAddress: {shop['address']}\nPhone: {shop['phone']}\nDirections: {shop['directions']}\n\n"

                # Send the prompt to Gemini for parsing the raw data into a structured format
                prompt = f"""
                Parse these medical shop details into a structured format. For each shop, extract:
                1. Name
                2. Address (the part with road/street name)
                3. Phone number (the 10-digit or landline number)

                Format as a list of dictionaries like this:
                [
                    {{
                        "name": "Shop Name",
                        "address": "Street address",
                        "phone": "Phone number",
                        "directions": "https://www.google.com/maps/search/?api=1&query=Shop+Name"
                    }} 
                ]

                Here are the details to parse:
                {shops_data}

                Return ONLY the Python list, no other text.
                """

                # Assuming 'model' is your Gemini model instance
                response = model.generate_content(prompt)
                shops = ast.literal_eval(response.text)  # Convert the response text into a Python object

                return shops

            except Exception as e:
                st.error(f"Error fetching data: {e}")
                return None
        else:
            st.warning("Please click the 'Get My Location' button to allow geolocation access.")
            return None

    if 'previous_task' not in st.session_state:
        st.session_state.previous_task = user_choice
    if st.session_state.previous_task != user_choice:
        st.session_state.show_hospitals = False
        st.session_state.show_medical_shops = False
        st.session_state.previous_task = user_choice

    if user_choice == "💊 First Aid":
    # Clear any hospital or medical shop results
        st.session_state.show_hospitals = False
        st.session_state.show_medical_shops = False

        user_emergency = st.text_input("Please describe your emergency:")
        if st.button("Get Advice"):
            if user_emergency:
                advice_found = provide_emergency_advice(user_emergency, first_aid_dataset)
                if advice_found:
                    st.success("Here is the advice for your emergency:")
                    st.write(advice_found['Emergency_Advice'])
                    if pd.notna(advice_found['Emergency_Image']):
                        st.image(advice_found['Emergency_Image'])
                    if pd.notna(advice_found['Emergency_Video']):
                        video_url = f"https://youtu.be/{advice_found['Emergency_Video']}"
                        st.video(video_url)
                else:
                    st.warning("No matching advice found in our database. Searching YouTube for relevant first aid videos...")
                    
                    # Call the updated `search_youtube` function with API key passed directly
                    video_title, video_url = search_youtube_emergency(user_emergency, yt_api_key)  # Replace with your actual API key
                    
                    if video_url:
                        st.info(f"Here's a relevant first aid video from YouTube: **{video_title}**")
                        st.video(video_url)
                    else:
                        st.error("Sorry, couldn't find any relevant videos.")
            else:
                st.warning("Please enter an emergency description.")

    elif user_choice == "🩹 Diagnosis and Medicine Recommendation":
    # Clear any hospital or medical shop results
        st.session_state.show_hospitals = False
        st.session_state.show_medical_shops = False

        # Arrange form fields in a cleaner layout
        col_left, col_right = st.columns(2)
        with col_left:
            patient_name = st.text_input("What is your name?")
        with col_right:
            patient_age = st.number_input("What is your age?", min_value=0)
        symptoms = st.text_area("What symptoms are you experiencing (comma-separated)?", height=100)

        if st.button("Get Diagnosis"):
            if patient_name and patient_age and symptoms:
                recommended_info = recommend_drug(symptoms, patient_age, dataset1, dataset2)
                if recommended_info:
                    st.success(f"Preliminary diagnosis based on symptoms: {recommended_info['Diagnosis']}")
                    st.write(f"Recommended medicine: {recommended_info['Medicine']}")
                    dosage_description = recommended_info['Dosage']
                    
                    # Pass the dosage description to Gemini for neat formatting
                    prompt = f"""
                    Format the following dosage information in a neat and easy-to-understand manner:
                    {dosage_description}
                    Provide a clean, formatted output with each medicine and its dosage on a separate line. Make it visually appealing with appropriate icons.
                    """

                    try:
                        # Assuming `model` is an instance of Gemini
                        response = model.generate_content(prompt)
                        st.markdown("---")
                        st.subheader("💊 Medication Dosage Instructions")

                        # Display the formatted response
                        st.markdown(response.text)

                    except Exception as e:
    
                        # Fallback to the original dosage description
                        st.write(f"💊 Recommended dosage according to age:: {dosage_description}")
                        st.write(f"Recommended advice related to symptoms: {recommended_info['Advice']}")

                    prompt = f"""
                    Based on this diagnosis: {recommended_info['Diagnosis']}
                    And these symptoms: {symptoms}
                    
                    Provide exactly 5 important points of advice. Format as a simple list with one emoji per point.
                    Return ONLY the list items without any other text.
                    Example format:
                    - 🏥 Visit your doctor regularly
                    - 💊 Take prescribed medicines as directed
                    - 🏠 Get adequate rest
                    - 🥗 Stay hydrated
                    - ⚠️ Seek emergency care if needed
                    """
                    
                    try:
                        response = model.generate_content(prompt)
                        st.markdown("---")
                        st.subheader("📋 Quick Health Tips")

                        # Split the response into lines and create bullet points
                        advice_points = [line.strip() for line in response.text.split('\n') if line.strip()]
                        for point in advice_points:
                            # Remove any existing bullet points or dashes
                            clean_point = point.lstrip('- •').strip()
                            st.write(f"• {clean_point}")

                    except Exception as e:
                        st.error("Could not generate additional advice.")

                    # Now using the search_youtube_for_remedies function
                    # Replace with your actual API key
                    video_title, video_url = search_youtube_for_remedies(symptoms, yt_api_key)

                    if video_url:
                        st.markdown(f"### YouTube Video: {video_title}")
                        st.video(video_url)
                    else:
                        st.warning("No relevant video found.")

                else:
                    st.warning("Sorry, no match found for the provided symptoms.")
            else:
                st.warning("Please fill in all fields.")
    
    elif user_choice == "🏥 Search Hospitals":
        st.session_state.show_hospitals = True
        st.session_state.show_medical_shops = False
        hospitals = search_and_format_hospitals()
        if hospitals:
            st.success("Found nearby hospitals!")
            for hospital in hospitals:
                with st.expander(f"🏥 {hospital['name']}"):
                    st.write(f"📍 **Address:** {hospital['address']}")
                    st.write(f"📞 **Phone:** {hospital['phone']}")
                    st.markdown(f"[🗺️ Get Directions]({hospital['directions']})")
        else:
            st.error("No hospitals found nearby.")

    elif user_choice == "💉 Search Medical Shops":
        st.session_state.show_hospitals = False
        st.session_state.show_medical_shops = True
        shops = search_and_format_medical_shops()
        if shops:
            st.success("Found nearby medical shops!")
            for shop in shops:
                with st.expander(f"💊 {shop['name']}"):
                    st.write(f"📍 **Address:** {shop['address']}")
                    st.write(f"📞 **Phone:** {shop['phone']}")
                    st.markdown(f"[🗺️ Get Directions]({shop['directions']})")
        else:
            st.error("No medical shops found nearby.")


if __name__ == "__main__":
    create_emergency_sidebar()
