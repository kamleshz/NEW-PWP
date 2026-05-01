
import datetime
import difflib
import os
import shutil
import time
from pathlib import Path
from threading import Lock

import pandas as pd
from lxml import html
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


STATE_DISTRICT_MASTER_RAW = """
ANDAMAN AND NICOBAR ISLANDS|Nicobar
ANDAMAN AND NICOBAR ISLANDS|North and Middle Andaman
ANDAMAN AND NICOBAR ISLANDS|South Andaman
ANDHRA PRADESH|Anantapur
ANDHRA PRADESH|Chittoor
ANDHRA PRADESH|East Godavari
ANDHRA PRADESH|Guntur
ANDHRA PRADESH|Krishna
ANDHRA PRADESH|Kurnool
ANDHRA PRADESH|Nellore
ANDHRA PRADESH|Prakasam
ANDHRA PRADESH|Srikakulam
ANDHRA PRADESH|Visakhapatnam
ANDHRA PRADESH|Vizianagaram
ANDHRA PRADESH|West Godavari
ANDHRA PRADESH|YSR Kadapa
ARUNACHAL PRADESH|Tawang
ARUNACHAL PRADESH|West Kameng
ARUNACHAL PRADESH|East Kameng
ARUNACHAL PRADESH|Papum Pare
ARUNACHAL PRADESH|Kurung Kumey
ARUNACHAL PRADESH|Kra Daadi
ARUNACHAL PRADESH|Lower Subansiri
ARUNACHAL PRADESH|Upper Subansiri
ARUNACHAL PRADESH|West Siang
ARUNACHAL PRADESH|East Siang
ARUNACHAL PRADESH|Siang
ARUNACHAL PRADESH|Upper Siang
ARUNACHAL PRADESH|Lower Siang
ARUNACHAL PRADESH|Lower Dibang Valley
ARUNACHAL PRADESH|Dibang Valley
ARUNACHAL PRADESH|Anjaw
ARUNACHAL PRADESH|Lohit
ARUNACHAL PRADESH|Namsai
ARUNACHAL PRADESH|Changlang
ARUNACHAL PRADESH|Tirap
ARUNACHAL PRADESH|Longding
ASSAM|Baksa
ASSAM|Barpeta
ASSAM|Biswanath
ASSAM|Bongaigaon
ASSAM|Cachar
ASSAM|Charaideo
ASSAM|Chirang
ASSAM|Darrang
ASSAM|Dhemaji
ASSAM|Dhubri
ASSAM|Dibrugarh
ASSAM|Goalpara
ASSAM|Golaghat
ASSAM|Hailakandi
ASSAM|Hojai
ASSAM|Jorhat
ASSAM|Kamrup Metropolitan
ASSAM|Kamrup
ASSAM|Karbi Anglong
ASSAM|Karimganj
ASSAM|Kokrajhar
ASSAM|Lakhimpur
ASSAM|Majuli
ASSAM|Morigaon
ASSAM|Nagaon
ASSAM|Nalbari
ASSAM|Dima Hasao
ASSAM|Sivasagar
ASSAM|Sonitpur
ASSAM|South Salmara-Mankachar
ASSAM|Tinsukia
ASSAM|Udalguri
ASSAM|West Karbi Anglong
BIHAR|Araria
BIHAR|Arwal
BIHAR|Aurangabad
BIHAR|Banka
BIHAR|Begusarai
BIHAR|Bhagalpur
BIHAR|Bhojpur
BIHAR|Buxar
BIHAR|Darbhanga
BIHAR|East Champaran (Motihari)
BIHAR|Gaya
BIHAR|Gopalganj
BIHAR|Jamui
BIHAR|Jehanabad
BIHAR|Kaimur (Bhabua)
BIHAR|Katihar
BIHAR|Khagaria
BIHAR|Kishanganj
BIHAR|Lakhisarai
BIHAR|Madhepura
BIHAR|Madhubani
BIHAR|Munger (Monghyr)
BIHAR|Muzaffarpur
BIHAR|Nalanda
BIHAR|Nawada
BIHAR|Patna
BIHAR|Purnia (Purnea)
BIHAR|Rohtas
BIHAR|Saharsa
BIHAR|Samastipur
BIHAR|Saran
BIHAR|Sheikhpura
BIHAR|Sheohar
BIHAR|Sitamarhi
BIHAR|Siwan
BIHAR|Supaul
BIHAR|Vaishali
BIHAR|West Champaran
CHANDIGARH|Chandigarh
CHHATTISGARH|Balod
CHHATTISGARH|Baloda Bazar
CHHATTISGARH|Balrampur
CHHATTISGARH|Bastar
CHHATTISGARH|Bemetara
CHHATTISGARH|Bijapur
CHHATTISGARH|Bilaspur
CHHATTISGARH|Dantewada (South Bastar)
CHHATTISGARH|Dhamtari
CHHATTISGARH|Durg
CHHATTISGARH|Gariyaband
CHHATTISGARH|Janjgir-Champa
CHHATTISGARH|Jashpur
CHHATTISGARH|Kabirdham (Kawardha)
CHHATTISGARH|Kanker (North Bastar)
CHHATTISGARH|Kondagaon
CHHATTISGARH|Korba
CHHATTISGARH|Korea (Koriya)
CHHATTISGARH|Mahasamund
CHHATTISGARH|Mungeli
CHHATTISGARH|Narayanpur
CHHATTISGARH|Raigarh
CHHATTISGARH|Raipur
CHHATTISGARH|Rajnandgaon
CHHATTISGARH|Sukma
CHHATTISGARH|Surajpur
CHHATTISGARH|Surguja
DADRA AND NAGAR HAVELI AND DAMAN AND DIU|Dadra & Nagar Haveli
DELHI|Central Delhi
DELHI|East Delhi
DELHI|New Delhi
DELHI|North Delhi
DELHI|North East Delhi
DELHI|North West Delhi
DELHI|Shahdara
DELHI|South Delhi
DELHI|South East Delhi
DELHI|South West Delhi
DELHI|West Delhi
GOA|North Goa
GOA|South Goa
GUJARAT|Ahmedabad
GUJARAT|Amreli
GUJARAT|Anand
GUJARAT|Aravalli
GUJARAT|Banaskantha (Palanpur)
GUJARAT|Bharuch
GUJARAT|Bhavnagar
GUJARAT|Botad
GUJARAT|Chhota Udepur
GUJARAT|Dahod
GUJARAT|Dangs (Ahwa)
GUJARAT|Devbhoomi Dwarka
GUJARAT|Gandhinagar
GUJARAT|Gir Somnath
GUJARAT|Jamnagar
GUJARAT|Junagadh
GUJARAT|Kachchh
GUJARAT|Kheda (Nadiad)
GUJARAT|Mahisagar
GUJARAT|Mehsana
GUJARAT|Morbi
GUJARAT|Narmada (Rajpipla)
GUJARAT|Navsari
GUJARAT|Panchmahal (Godhra)
GUJARAT|Patan
GUJARAT|Porbandar
GUJARAT|Rajkot
GUJARAT|Sabarkantha (Himmatnagar)
GUJARAT|Surat
GUJARAT|Surendranagar
GUJARAT|Tapi (Vyara)
GUJARAT|Vadodara
GUJARAT|Valsad
HARYANA|Ambala
HARYANA|Bhiwani
HARYANA|Charkhi Dadri
HARYANA|Faridabad
HARYANA|Fatehabad
HARYANA|Gurgaon
HARYANA|Hisar
HARYANA|Jhajjar
HARYANA|Jind
HARYANA|Kaithal
HARYANA|Karnal
HARYANA|Kurukshetra
HARYANA|Mahendragarh
HARYANA|Mewat
HARYANA|Palwal
HARYANA|Panchkula
HARYANA|Panipat
HARYANA|Rewari
HARYANA|Rohtak
HARYANA|Sirsa
HARYANA|Sonipat
HARYANA|Yamunanagar
HIMACHAL PRADESH|Bilaspur
HIMACHAL PRADESH|Chamba
HIMACHAL PRADESH|Hamirpur
HIMACHAL PRADESH|Kangra
HIMACHAL PRADESH|Kinnaur
HIMACHAL PRADESH|Kullu
HIMACHAL PRADESH|Lahaul & Spiti
HIMACHAL PRADESH|Mandi
HIMACHAL PRADESH|Shimla
HIMACHAL PRADESH|Sirmaur (Sirmour)
HIMACHAL PRADESH|Solan
HIMACHAL PRADESH|Una
JAMMU AND KASHMIR|Anantnag
JAMMU AND KASHMIR|Bandipore
JAMMU AND KASHMIR|Baramulla
JAMMU AND KASHMIR|Budgam
JAMMU AND KASHMIR|Doda
JAMMU AND KASHMIR|Ganderbal
JAMMU AND KASHMIR|Jammu
JAMMU AND KASHMIR|Kargil
JAMMU AND KASHMIR|Kathua
JAMMU AND KASHMIR|Kishtwar
JAMMU AND KASHMIR|Kulgam
JAMMU AND KASHMIR|Kupwara
JAMMU AND KASHMIR|Leh
JAMMU AND KASHMIR|Poonch
JAMMU AND KASHMIR|Pulwama
JAMMU AND KASHMIR|Rajouri
JAMMU AND KASHMIR|Ramban
JAMMU AND KASHMIR|Reasi
JAMMU AND KASHMIR|Samba
JAMMU AND KASHMIR|Shopian
JAMMU AND KASHMIR|Srinagar
JAMMU AND KASHMIR|Udhampur
JHARKHAND|Bokaro
JHARKHAND|Chatra
JHARKHAND|Deoghar
JHARKHAND|Dhanbad
JHARKHAND|Dumka
JHARKHAND|East Singhbhum
JHARKHAND|Garhwa
JHARKHAND|Giridih
JHARKHAND|Godda
JHARKHAND|Gumla
JHARKHAND|Hazaribag
JHARKHAND|Jamtara
JHARKHAND|Khunti
JHARKHAND|Koderma
JHARKHAND|Latehar
JHARKHAND|Lohardaga
JHARKHAND|Pakur
JHARKHAND|Palamu
JHARKHAND|Ramgarh
JHARKHAND|Ranchi
JHARKHAND|Sahibganj
JHARKHAND|Seraikela-Kharsawan
JHARKHAND|Simdega
JHARKHAND|West Singhbhum
KARNATAKA|Bagalkot
KARNATAKA|Ballari (Bellary)
KARNATAKA|Belagavi (Belgaum)
KARNATAKA|Bengaluru (Bangalore) Rural
KARNATAKA|Bengaluru (Bangalore) Urban
KARNATAKA|Bidar
KARNATAKA|Chamarajanagar
KARNATAKA|Chikballapur
KARNATAKA|Chikkamagaluru (Chikmagalur)
KARNATAKA|Chitradurga
KARNATAKA|Dakshina Kannada
KARNATAKA|Davangere
KARNATAKA|Dharwad
KARNATAKA|Gadag
KARNATAKA|Hassan
KARNATAKA|Haveri
KARNATAKA|Kalaburagi (Gulbarga)
KARNATAKA|Kodagu
KARNATAKA|Kolar
KARNATAKA|Koppal
KARNATAKA|Mandya
KARNATAKA|Mysuru (Mysore)
KARNATAKA|Raichur
KARNATAKA|Ramanagara
KARNATAKA|Shivamogga (Shimoga)
KARNATAKA|Tumakuru (Tumkur)
KARNATAKA|Udupi
KARNATAKA|Uttara Kannada (Karwar)
KARNATAKA|Vijayapura (Bijapur)
KARNATAKA|Yadgir
KERALA|Alappuzha
KERALA|Ernakulam
KERALA|Idukki
KERALA|Kannur
KERALA|Kasaragod
KERALA|Kollam
KERALA|Kottayam
KERALA|Kozhikode
KERALA|Malappuram
KERALA|Palakkad
KERALA|Pathanamthitta
KERALA|Thiruvananthapuram
KERALA|Thrissur
KERALA|Wayanad
LADAKH|Kargil
LADAKH|Leh
LAKSHADWEEP|Agatti
LAKSHADWEEP|Amini
LAKSHADWEEP|Androth
LAKSHADWEEP|Bithra
LAKSHADWEEP|Chethlath
LAKSHADWEEP|Kavaratti
LAKSHADWEEP|Kadmath
LAKSHADWEEP|Kalpeni
LAKSHADWEEP|Kilthan
LAKSHADWEEP|Minicoy
MADHYA PRADESH|Agar Malwa
MADHYA PRADESH|Alirajpur
MADHYA PRADESH|Anuppur
MADHYA PRADESH|Ashoknagar
MADHYA PRADESH|Balaghat
MADHYA PRADESH|Barwani
MADHYA PRADESH|Betul
MADHYA PRADESH|Bhind
MADHYA PRADESH|Bhopal
MADHYA PRADESH|Burhanpur
MADHYA PRADESH|Chhatarpur
MADHYA PRADESH|Chhindwara
MADHYA PRADESH|Damoh
MADHYA PRADESH|Datia
MADHYA PRADESH|Dewas
MADHYA PRADESH|Dhar
MADHYA PRADESH|Dindori
MADHYA PRADESH|Guna
MADHYA PRADESH|Gwalior
MADHYA PRADESH|Harda
MADHYA PRADESH|Hoshangabad
MADHYA PRADESH|Indore
MADHYA PRADESH|Jabalpur
MADHYA PRADESH|Jhabua
MADHYA PRADESH|Katni
MADHYA PRADESH|Khandwa
MADHYA PRADESH|Khargone
MADHYA PRADESH|Mandla
MADHYA PRADESH|Mandsaur
MADHYA PRADESH|Morena
MADHYA PRADESH|Narsinghpur
MADHYA PRADESH|Neemuch
MADHYA PRADESH|Panna
MADHYA PRADESH|Raisen
MADHYA PRADESH|Rajgarh
MADHYA PRADESH|Ratlam
MADHYA PRADESH|Rewa
MADHYA PRADESH|Sagar
MADHYA PRADESH|Satna
MADHYA PRADESH|Sehore
MADHYA PRADESH|Seoni
MADHYA PRADESH|Shahdol
MADHYA PRADESH|Shajapur
MADHYA PRADESH|Sheopur
MADHYA PRADESH|Shivpuri
MADHYA PRADESH|Sidhi
MADHYA PRADESH|Singrauli
MADHYA PRADESH|Tikamgarh
MADHYA PRADESH|Ujjain
MADHYA PRADESH|Umaria
MADHYA PRADESH|Vidisha
MAHARASHTRA|Ahmednagar
MAHARASHTRA|Akola
MAHARASHTRA|Amravati
MAHARASHTRA|Aurangabad
MAHARASHTRA|Beed
MAHARASHTRA|Bhandara
MAHARASHTRA|Buldhana
MAHARASHTRA|Chandrapur
MAHARASHTRA|Dhule
MAHARASHTRA|Gadchiroli
MAHARASHTRA|Gondia
MAHARASHTRA|Hingoli
MAHARASHTRA|Jalgaon
MAHARASHTRA|Jalna
MAHARASHTRA|Kolhapur
MAHARASHTRA|Latur
MAHARASHTRA|Mumbai City
MAHARASHTRA|Mumbai Suburban
MAHARASHTRA|Nagpur
MAHARASHTRA|Nanded
MAHARASHTRA|Nandurbar
MAHARASHTRA|Nashik
MAHARASHTRA|Osmanabad
MAHARASHTRA|Palghar
MAHARASHTRA|Parbhani
MAHARASHTRA|Pune
MAHARASHTRA|Raigad
MAHARASHTRA|Ratnagiri
MAHARASHTRA|Sangli
MAHARASHTRA|Satara
MAHARASHTRA|Sindhudurg
MAHARASHTRA|Solapur
MAHARASHTRA|Thane
MAHARASHTRA|Wardha
MAHARASHTRA|Washim
MAHARASHTRA|Yavatmal
MANIPUR|Bishnupur
MANIPUR|Chandel
MANIPUR|Churachandpur
MANIPUR|Imphal East
MANIPUR|Imphal West
MANIPUR|Jiribam
MANIPUR|Kakching
MANIPUR|Kamjong
MANIPUR|Kangpokpi
MANIPUR|Noney
MANIPUR|Pherzawl
MANIPUR|Senapati
MANIPUR|Tamenglong
MANIPUR|Tengnoupal
MANIPUR|Thoubal
MANIPUR|Ukhrul
MEGHALAYA|East Garo Hills
MEGHALAYA|East Jaintia Hills
MEGHALAYA|East Khasi Hills
MEGHALAYA|North Garo Hills
MEGHALAYA|Ri Bhoi
MEGHALAYA|South Garo Hills
MEGHALAYA|South West Garo Hills
MEGHALAYA|South West Khasi Hills
MEGHALAYA|West Garo Hills
MEGHALAYA|West Jaintia Hills
MEGHALAYA|West Khasi Hills
MIZORAM|Aizawl
MIZORAM|Champhai
MIZORAM|Kolasib
MIZORAM|Lawngtlai
MIZORAM|Lunglei
MIZORAM|Mamit
MIZORAM|Saiha
MIZORAM|Serchhip
NAGALAND|Dimapur
NAGALAND|Kiphire
NAGALAND|Kohima
NAGALAND|Longleng
NAGALAND|Mokokchung
NAGALAND|Mon
NAGALAND|Peren
NAGALAND|Phek
NAGALAND|Tuensang
NAGALAND|Wokha
NAGALAND|Zunheboto
ODISHA|Angul
ODISHA|Balangir
ODISHA|Balasore
ODISHA|Bargarh
ODISHA|Bhadrak
ODISHA|Boudh
ODISHA|Cuttack
ODISHA|Deogarh
ODISHA|Dhenkanal
ODISHA|Gajapati
ODISHA|Ganjam
ODISHA|Jagatsinghapur
ODISHA|Jajpur
ODISHA|Jharsuguda
ODISHA|Kalahandi
ODISHA|Kandhamal
ODISHA|Kendrapara
ODISHA|Kendujhar (Keonjhar)
ODISHA|Khordha
ODISHA|Koraput
ODISHA|Malkangiri
ODISHA|Mayurbhanj
ODISHA|Nabarangpur
ODISHA|Nayagarh
ODISHA|Nuapada
ODISHA|Puri
ODISHA|Rayagada
ODISHA|Sambalpur
ODISHA|Sonepur
ODISHA|Sundargarh
PONDICHERRY|Pondicherry
PONDICHERRY|Karaikal
PONDICHERRY|Mahe
PONDICHERRY|Yanam
PUNJAB|Amritsar
PUNJAB|Barnala
PUNJAB|Bathinda
PUNJAB|Faridkot
PUNJAB|Fatehgarh Sahib
PUNJAB|Fazilka
PUNJAB|Ferozepur
PUNJAB|Gurdaspur
PUNJAB|Hoshiarpur
PUNJAB|Jalandhar
PUNJAB|Kapurthala
PUNJAB|Ludhiana
PUNJAB|Mansa
PUNJAB|Moga
PUNJAB|Muktsar
PUNJAB|Nawanshahr (Shahid Bhagat Singh Nagar)
PUNJAB|Pathankot
PUNJAB|Patiala
PUNJAB|Rupnagar
PUNJAB|Sahibzada Ajit Singh Nagar (Mohali)
PUNJAB|Sangrur
PUNJAB|Tarn Taran
RAJASTHAN|Ajmer
RAJASTHAN|Alwar
RAJASTHAN|Banswara
RAJASTHAN|Baran
RAJASTHAN|Barmer
RAJASTHAN|Bharatpur
RAJASTHAN|Bhilwara
RAJASTHAN|Bikaner
RAJASTHAN|Bundi
RAJASTHAN|Chittorgarh
RAJASTHAN|Churu
RAJASTHAN|Dausa
RAJASTHAN|Dholpur
RAJASTHAN|Dungarpur
RAJASTHAN|Hanumangarh
RAJASTHAN|Jaipur
RAJASTHAN|Jaisalmer
RAJASTHAN|Jalore
RAJASTHAN|Jhalawar
RAJASTHAN|Jhunjhunu
RAJASTHAN|Jodhpur
RAJASTHAN|Karauli
RAJASTHAN|Kota
RAJASTHAN|Nagaur
RAJASTHAN|Pali
RAJASTHAN|Pratapgarh
RAJASTHAN|Rajsamand
RAJASTHAN|Sawai Madhopur
RAJASTHAN|Sikar
RAJASTHAN|Sirohi
RAJASTHAN|Sri Ganganagar
RAJASTHAN|Tonk
RAJASTHAN|Udaipur
SIKKIM|East Sikkim
SIKKIM|North Sikkim
SIKKIM|South Sikkim
SIKKIM|West Sikkim
TAMIL NADU|Ariyalur
TAMIL NADU|Chennai
TAMIL NADU|Coimbatore
TAMIL NADU|Cuddalore
TAMIL NADU|Dharmapuri
TAMIL NADU|Dindigul
TAMIL NADU|Erode
TAMIL NADU|Kanchipuram
TAMIL NADU|Kanyakumari
TAMIL NADU|Karur
TAMIL NADU|Krishnagiri
TAMIL NADU|Madurai
TAMIL NADU|Nagapattinam
TAMIL NADU|Namakkal
TAMIL NADU|Nilgiris
TAMIL NADU|Perambalur
TAMIL NADU|Pudukkottai
TAMIL NADU|Ramanathapuram
TAMIL NADU|Salem
TAMIL NADU|Sivaganga
TAMIL NADU|Thanjavur
TAMIL NADU|Theni
TAMIL NADU|Thoothukudi (Tuticorin)
TAMIL NADU|Tiruchirappalli
TAMIL NADU|Tirunelveli
TAMIL NADU|Tiruppur
TAMIL NADU|Tiruvallur
TAMIL NADU|Tiruvannamalai
TAMIL NADU|Tiruvarur
TAMIL NADU|Vellore
TAMIL NADU|Viluppuram
TAMIL NADU|Virudhunagar
TELANGANA|Adilabad
TELANGANA|Bhadradri Kothagudem
TELANGANA|Hyderabad
TELANGANA|Jagtial
TELANGANA|Jangaon
TELANGANA|Jayashankar Bhoopalpally
TELANGANA|Jogulamba Gadwal
TELANGANA|Kamareddy
TELANGANA|Karimnagar
TELANGANA|Khammam
TELANGANA|Komaram Bheem Asifabad
TELANGANA|Mahabubabad
TELANGANA|Mahabubnagar
TELANGANA|Mancherial
TELANGANA|Medak
TELANGANA|Medchal
TELANGANA|Nagarkurnool
TELANGANA|Nalgonda
TELANGANA|Nirmal
TELANGANA|Nizamabad
TELANGANA|Peddapalli
TELANGANA|Rajanna Sircilla
TELANGANA|Rangareddy
TELANGANA|Sangareddy
TELANGANA|Siddipet
TELANGANA|Suryapet
TELANGANA|Vikarabad
TELANGANA|Wanaparthy
TELANGANA|Warangal (Rural)
TELANGANA|Warangal (Urban)
TELANGANA|Yadadri Bhuvanagiri
TRIPURA|Dhalai
TRIPURA|Gomati
TRIPURA|Khowai
TRIPURA|North Tripura
TRIPURA|Sepahijala
TRIPURA|South Tripura
TRIPURA|Unakoti
TRIPURA|West Tripura
UTTAR PRADESH|Agra
UTTAR PRADESH|Aligarh
UTTAR PRADESH|Allahabad
UTTAR PRADESH|Ambedkar Nagar
UTTAR PRADESH|Amethi (Chatrapati Sahuji Mahraj Nagar)
UTTAR PRADESH|Amroha (J.P. Nagar)
UTTAR PRADESH|Auraiya
UTTAR PRADESH|Azamgarh
UTTAR PRADESH|Baghpat
UTTAR PRADESH|Bahraich
UTTAR PRADESH|Ballia
UTTAR PRADESH|Balrampur
UTTAR PRADESH|Banda
UTTAR PRADESH|Barabanki
UTTAR PRADESH|Bareilly
UTTAR PRADESH|Basti
UTTAR PRADESH|Bhadohi
UTTAR PRADESH|Bijnor
UTTAR PRADESH|Budaun
UTTAR PRADESH|Bulandshahr
UTTAR PRADESH|Chandauli
UTTAR PRADESH|Chitrakoot
UTTAR PRADESH|Deoria
UTTAR PRADESH|Etah
UTTAR PRADESH|Etawah
UTTAR PRADESH|Faizabad
UTTAR PRADESH|Farrukhabad
UTTAR PRADESH|Fatehpur
UTTAR PRADESH|Firozabad
UTTAR PRADESH|Gautam Buddha Nagar
UTTAR PRADESH|Ghaziabad
UTTAR PRADESH|Ghazipur
UTTAR PRADESH|Gonda
UTTAR PRADESH|Gorakhpur
UTTAR PRADESH|Hamirpur
UTTAR PRADESH|Hapur (Panchsheel Nagar)
UTTAR PRADESH|Hardoi
UTTAR PRADESH|Hathras
UTTAR PRADESH|Jalaun
UTTAR PRADESH|Jaunpur
UTTAR PRADESH|Jhansi
UTTAR PRADESH|Kannauj
UTTAR PRADESH|Kanpur Dehat
UTTAR PRADESH|Kanpur Nagar
UTTAR PRADESH|Kanshiram Nagar (Kasganj)
UTTAR PRADESH|Kaushambi
UTTAR PRADESH|Kushinagar (Padrauna)
UTTAR PRADESH|Lakhimpur - Kheri
UTTAR PRADESH|Lalitpur
UTTAR PRADESH|Lucknow
UTTAR PRADESH|Maharajganj
UTTAR PRADESH|Mahoba
UTTAR PRADESH|Mainpuri
UTTAR PRADESH|Mathura
UTTAR PRADESH|Mau
UTTAR PRADESH|Meerut
UTTAR PRADESH|Mirzapur
UTTAR PRADESH|Moradabad
UTTAR PRADESH|Muzaffarnagar
UTTAR PRADESH|Pilibhit
UTTAR PRADESH|Pratapgarh
UTTAR PRADESH|RaeBareli
UTTAR PRADESH|Rampur
UTTAR PRADESH|Saharanpur
UTTAR PRADESH|Sambhal (Bhim Nagar)
UTTAR PRADESH|Sant Kabir Nagar
UTTAR PRADESH|Shahjahanpur
UTTAR PRADESH|Shamali (Prabuddh Nagar)
UTTAR PRADESH|Shravasti
UTTAR PRADESH|Siddharth Nagar
UTTAR PRADESH|Sitapur
UTTAR PRADESH|Sonbhadra
UTTAR PRADESH|Sultanpur
UTTAR PRADESH|Unnao
UTTAR PRADESH|Varanasi
UTTARAKHAND|Almora
UTTARAKHAND|Bageshwar
UTTARAKHAND|Chamoli
UTTARAKHAND|Champawat
UTTARAKHAND|Dehradun
UTTARAKHAND|Haridwar
UTTARAKHAND|Nainital
UTTARAKHAND|Pauri Garhwal
UTTARAKHAND|Pithoragarh
UTTARAKHAND|Rudraprayag
UTTARAKHAND|Tehri Garhwal
UTTARAKHAND|Udham Singh Nagar
UTTARAKHAND|Uttarkashi
WEST BENGAL|Alipurduar
WEST BENGAL|Bankura
WEST BENGAL|Birbhum
WEST BENGAL|Burdwan (Bardhaman)
WEST BENGAL|Cooch Behar
WEST BENGAL|Dakshin Dinajpur (South Dinajpur)
WEST BENGAL|Darjeeling
WEST BENGAL|Hooghly
WEST BENGAL|Howrah
WEST BENGAL|Jalpaiguri
WEST BENGAL|Kalimpong
WEST BENGAL|Kolkata
WEST BENGAL|Malda
WEST BENGAL|Murshidabad
WEST BENGAL|Nadia
WEST BENGAL|North 24 Parganas
WEST BENGAL|Paschim Medinipur (West Medinipur)
WEST BENGAL|Purba Medinipur (East Medinipur)
WEST BENGAL|Purulia
WEST BENGAL|South 24 Parganas
WEST BENGAL|Uttar Dinajpur (North Dinajpur)
""".strip()


def custom_wait_clickable_and_click(driver, locator, attempts=10):
    count = 0
    while count < attempts:
        try:
            elem = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(locator))
            elem.click()
            return
        except Exception as exc:
            print(f"Attempt {count + 1} failed: {exc}")
            time.sleep(1)
            count += 1
    driver.save_screenshot(f"error_{locator[1]}.png")
    raise RuntimeError(f"Failed to click element: {locator}")


def normalize_place_name(value):
    return " ".join(str(value).strip().upper().split())


def normalize_district_lookup_name(value):
    cleaned_value = normalize_place_name(value)
    cleaned_value = cleaned_value.split("(", 1)[0].strip()
    cleaned_value = "".join(char if char.isalnum() or char.isspace() else " " for char in cleaned_value)
    return " ".join(cleaned_value.split())


def build_state_district_master():
    state_district_map = {}
    state_name_map = {}
    district_lookup_map = {}
    for line in STATE_DISTRICT_MASTER_RAW.splitlines():
        state, district = [part.strip() for part in line.split("|", 1)]
        state_key = normalize_place_name(state)
        district_key = normalize_place_name(district)
        district_name = " ".join(district.split())
        state_district_map.setdefault(state_key, {})
        state_district_map[state_key][district_key] = district_name
        state_name_map[state_key] = " ".join(state.split())
        district_lookup_map.setdefault(state_key, {})
        district_lookup_key = normalize_district_lookup_name(district)
        district_lookup_map[state_key][district_lookup_key] = district_name
    return state_district_map, state_name_map, district_lookup_map


STATE_DISTRICT_MASTER, STATE_NAME_MASTER, DISTRICT_LOOKUP_MASTER = build_state_district_master()


def get_state_suggestion(state_name):
    matches = difflib.get_close_matches(
        normalize_place_name(state_name),
        list(STATE_NAME_MASTER.keys()),
        n=1,
        cutoff=0.6,
    )
    if not matches:
        return ""
    return STATE_NAME_MASTER[matches[0]]


def get_district_suggestion(state_key, district_name):
    districts = STATE_DISTRICT_MASTER.get(state_key, {})
    district_lookup = DISTRICT_LOOKUP_MASTER.get(state_key, {})
    district_lookup_key = normalize_district_lookup_name(district_name)

    if district_lookup_key in district_lookup:
        return district_lookup[district_lookup_key]

    matches = difflib.get_close_matches(
        normalize_place_name(district_name),
        list(districts.keys()),
        n=1,
        cutoff=0.6,
    )
    if matches:
        return districts[matches[0]]

    lookup_matches = difflib.get_close_matches(
        district_lookup_key,
        list(district_lookup.keys()),
        n=1,
        cutoff=0.6,
    )
    if not lookup_matches:
        return ""
    return district_lookup[lookup_matches[0]]


def get_district_match_details(state_key, district_name):
    districts = STATE_DISTRICT_MASTER.get(state_key, {})
    district_lookup = DISTRICT_LOOKUP_MASTER.get(state_key, {})
    full_district_key = normalize_place_name(district_name)
    lookup_district_key = normalize_district_lookup_name(district_name)

    if full_district_key in districts:
        return True, districts[full_district_key], False

    if lookup_district_key in district_lookup:
        return False, district_lookup[lookup_district_key], True

    full_matches = difflib.get_close_matches(
        full_district_key,
        list(districts.keys()),
        n=1,
        cutoff=0.5,
    )
    if full_matches:
        return False, districts[full_matches[0]], True

    lookup_matches = difflib.get_close_matches(
        lookup_district_key,
        list(district_lookup.keys()),
        n=1,
        cutoff=0.5,
    )
    if lookup_matches:
        return False, district_lookup[lookup_matches[0]], True

    return False, "", False


def get_state_and_district_suggestion(state_name, district_name):
    suggested_state = get_state_suggestion(state_name)
    suggested_district = ""
    if suggested_state:
        suggested_state_key = normalize_place_name(suggested_state)
        suggested_district = get_district_suggestion(suggested_state_key, district_name)
    return suggested_state, suggested_district


def get_state_validation_message(suggested_state):
    if suggested_state:
        return "State spelling mismatch. Use Suggested State."
    return "State name not found in master list."


def build_name_of_entity_value(row):
    registration_type = normalize_place_name(row.get("Registration Type", ""))
    application_number = " ".join(str(row.get("Application Number", "")).strip().split())
    entity_name = " ".join(str(row.get("Entity Name", "")).strip().split())
    existing_name = " ".join(str(row.get("Name of the Entity", "")).strip().split())

    if registration_type == "REGISTERED":
        if application_number and entity_name:
            return f"{application_number} - {entity_name}"
        if entity_name:
            return entity_name
        return existing_name

    if entity_name:
        return entity_name
    return existing_name


def prepare_name_of_entity_column(df):
    prepared_df = df.copy()
    prepared_df["Name of the Entity"] = prepared_df.apply(build_name_of_entity_value, axis=1)
    return prepared_df


class PWPBotService:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.upload_dir = self.base_dir / "uploads"
        self.output_dir = self.base_dir / "outputs"
        self.upload_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.driver = None
        self.logged_in = False
        self.run_lock = Lock()

    def _timestamp(self):
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    def _is_headless_enabled(self):
        default_value = "1" if os.name != "nt" else "0"
        return os.getenv("PWP_HEADLESS", default_value) == "1"

    def _configure_common_browser_flags(self, options):
        if self._is_headless_enabled():
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-blink-features=AutomationControlled")

    def _build_chrome_driver(self):
        options = ChromeOptions()
        self._configure_common_browser_flags(options)
        chrome_binary = (
            os.getenv("CHROME_BIN")
            or os.getenv("GOOGLE_CHROME_BIN")
            or shutil.which("chromium")
            or shutil.which("chromium-browser")
            or shutil.which("google-chrome")
            or shutil.which("chrome")
        )
        if chrome_binary:
            options.binary_location = chrome_binary

        driver_path = os.getenv("CHROMEDRIVER_PATH") or shutil.which("chromedriver")
        if driver_path:
            return webdriver.Chrome(service=ChromeService(driver_path), options=options)
        return webdriver.Chrome(options=options)

    def _build_edge_driver(self):
        options = EdgeOptions()
        self._configure_common_browser_flags(options)
        driver_path = os.getenv("EDGEDRIVER_PATH") or shutil.which("msedgedriver")
        if driver_path:
            return webdriver.Edge(service=EdgeService(driver_path), options=options)
        return webdriver.Edge(options=options)

    def _build_driver(self):
        remote_url = os.getenv("SELENIUM_REMOTE_URL", "").strip()
        preferred_browser = os.getenv("PWP_BROWSER", "").strip().lower()

        if remote_url:
            options = ChromeOptions()
            self._configure_common_browser_flags(options)
            chrome_binary = os.getenv("CHROME_BIN") or os.getenv("GOOGLE_CHROME_BIN")
            if chrome_binary:
                options.binary_location = chrome_binary
            return webdriver.Remote(command_executor=remote_url, options=options)

        if preferred_browser in {"chrome", "chromium"} or os.name != "nt":
            return self._build_chrome_driver()
        return self._build_edge_driver()

    def _require_login(self):
        if not self.driver:
            raise RuntimeError("Login is required before using this action.")

    def _open_sales_page(self):
        self.driver.get("https://eprplastic.cpcb.gov.in/#/epr/details/sales")
        time.sleep(1)

    def save_upload(self, file_storage, prefix):
        timestamp = self._timestamp()
        safe_name = Path(file_storage.filename).name
        destination = self.upload_dir / f"{prefix}_{timestamp}_{safe_name}"
        file_storage.save(destination)
        return destination

    def save_pdf_uploads(self, files):
        saved_paths = []
        for index, file_storage in enumerate(files, start=1):
            saved_paths.append(self.save_upload(file_storage, f"pdf_{index}"))
        return saved_paths

    def run_exclusive(self, func, *args, **kwargs):
        with self.run_lock:
            return func(*args, **kwargs)

    def file_payload(self, path):
        return {
            "name": Path(path).name,
            "download_url": f"/files/{Path(path).name}",
        }

    def login(self, email, password):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass

        self.driver = self._build_driver()
        self.driver.implicitly_wait(15)
        self.driver.get("https://eprplastic.cpcb.gov.in/#/plastic/home")
        time.sleep(1)

        pwp_button_locator = (
            By.XPATH,
            "/html/body/app-root/app-plastic/div/app-home-new/div/div/div[3]/div/div/div[1]/h6/label[2]/input",
        )
        custom_wait_clickable_and_click(self.driver, pwp_button_locator)

        action = ActionChains(self.driver)
        action.click(on_element=self.driver.find_element(by=By.XPATH, value='//*[@id="user_name"]')).perform()
        action.click(on_element=self.driver.find_element(by=By.XPATH, value='//*[@id="password_pass"]')).perform()
        self.driver.find_element(by=By.XPATH, value='//*[@id="user_name"]').send_keys(email)
        self.driver.find_element(by=By.XPATH, value='//*[@id="password_pass"]').send_keys(password)

        self.logged_in = True
        return {
            "message": "Browser opened and credentials filled. Complete any captcha or final login step in the browser if the portal asks for it.",
            "cookies_count": len(self.driver.get_cookies()),
        }

    def validate_state_district_data(self, df, source_file_path=None):
        if "State" not in df.columns or "District" not in df.columns:
            raise ValueError("Uploaded file must contain 'State' and 'District' columns.")

        prepared_df = prepare_name_of_entity_column(df)
        validation_errors = []
        validation_audit = []

        for index, row in prepared_df.iterrows():
            state_name = " ".join(str(row.get("State", "")).strip().split())
            district_name = " ".join(str(row.get("District", "")).strip().split())
            audit_row = {
                "Excel Row": index + 2,
                "State": state_name,
                "District": district_name,
                "Name of the Entity": " ".join(str(row.get("Name of the Entity", "")).strip().split()),
                "Suggested State": "",
                "Suggested District": "",
                "Validation Result": "",
            }

            if not state_name and not district_name:
                audit_row["Validation Result"] = "Skipped: State and District both blank."
                validation_audit.append(audit_row)
                continue

            if not state_name or not district_name:
                suggested_state, suggested_district = get_state_and_district_suggestion(state_name, district_name)
                audit_row["Suggested State"] = suggested_state
                audit_row["Suggested District"] = suggested_district
                audit_row["Validation Result"] = "Error: State or District is blank."
                validation_audit.append(audit_row)
                validation_errors.append(
                    {
                        "Excel Row": index + 2,
                        "State": state_name,
                        "District": district_name,
                        "Suggested State": suggested_state,
                        "Suggested District": suggested_district,
                        "Validation Error": "State or District is blank.",
                    }
                )
                continue

            state_key = normalize_place_name(state_name)
            district_key = normalize_place_name(district_name)

            if state_key not in STATE_DISTRICT_MASTER:
                suggested_state, suggested_district = get_state_and_district_suggestion(state_name, district_name)
                validation_message = get_state_validation_message(suggested_state)
                audit_row["Suggested State"] = suggested_state
                audit_row["Suggested District"] = suggested_district
                audit_row["Validation Result"] = f"Error: {validation_message}"
                validation_audit.append(audit_row)
                validation_errors.append(
                    {
                        "Excel Row": index + 2,
                        "State": state_name,
                        "District": district_name,
                        "Suggested State": suggested_state,
                        "Suggested District": suggested_district,
                        "Validation Error": validation_message,
                    }
                )
                continue

            is_exact_district_match, suggested_district, is_spelling_match = get_district_match_details(state_key, district_name)
            if not is_exact_district_match:
                validation_message = (
                    "District spelling mismatch. Use Suggested District."
                    if is_spelling_match and suggested_district
                    else "District does not belong to the selected state."
                )
                audit_row["Suggested State"] = STATE_NAME_MASTER[state_key]
                audit_row["Suggested District"] = suggested_district
                audit_row["Validation Result"] = f"Error: {validation_message}"
                validation_audit.append(audit_row)
                validation_errors.append(
                    {
                        "Excel Row": index + 2,
                        "State": state_name,
                        "District": district_name,
                        "Suggested State": STATE_NAME_MASTER[state_key],
                        "Suggested District": suggested_district,
                        "Validation Error": validation_message,
                    }
                )
                continue

            audit_row["Suggested State"] = STATE_NAME_MASTER[state_key]
            audit_row["Suggested District"] = STATE_DISTRICT_MASTER[state_key][district_key]
            audit_row["Validation Result"] = "Valid"
            validation_audit.append(audit_row)

        timestamp = self._timestamp()
        save_folder = Path(source_file_path).resolve().parent if source_file_path else self.output_dir
        prepared_file_path = ""
        if source_file_path:
            source_path = Path(source_file_path).resolve()
            prepared_file_path = source_path.parent / f"{source_path.stem}_prepared_{timestamp}.xlsx"
            prepared_df.to_excel(prepared_file_path, index=False, engine="openpyxl")

        payload = {
            "valid": not bool(validation_errors),
            "prepared_data": prepared_df,
            "files": [],
        }

        if validation_errors:
            validation_df = pd.DataFrame(validation_errors)
            validation_audit_df = pd.DataFrame(validation_audit)
            validation_file_path = save_folder / f"district_validation_errors_{timestamp}.xlsx"
            with pd.ExcelWriter(validation_file_path, engine="openpyxl") as writer:
                validation_df.to_excel(writer, sheet_name="Errors", index=False)
                validation_audit_df.to_excel(writer, sheet_name="Audit", index=False)
                prepared_df.to_excel(writer, sheet_name="Prepared Data", index=False)
            if prepared_file_path:
                payload["files"].append(self.file_payload(prepared_file_path))
            payload["files"].append(self.file_payload(validation_file_path))
            payload["message"] = "Validation failed. Download the prepared file and correction report."
            return payload

        if prepared_file_path:
            payload["files"].append(self.file_payload(prepared_file_path))
        payload["message"] = "State and district validation completed successfully."
        return payload

    def validate_excel_file(self, file_path):
        df = pd.read_excel(file_path, keep_default_na=False)
        result = self.validate_state_district_data(df, file_path)
        result.pop("prepared_data", None)
        return result

    def data_upload(self, file_path, upload_mode):
        self._require_login()
        df = pd.read_excel(
            file_path,
            keep_default_na=False,
            converters={
                "Bank Account No": str,
                "HSN Code": str,
                "E-Invoice Number": str,
                "IFSC Code": str,
            },
        )
        df["Quantity In MT"] = df["Quantity In MT"].astype("float64")
        df["Sales date"] = df["Sales date"].astype(str)
        df["Principal Amount"] = df["Principal Amount"].astype("float64")
        df["GST Amount"] = df["GST Amount"].astype("float64")

        validation_result = self.validate_state_district_data(df, file_path)
        df = validation_result["prepared_data"]
        if not validation_result["valid"]:
            validation_result.pop("prepared_data", None)
            return validation_result

        errors = []
        invoices = []
        mode = upload_mode.lower().strip()
        if mode == "export":
            upload_button_text = "Add New Export "
            output_prefix = "export_output_file"
        elif mode == "normal":
            upload_button_text = "Add New "
            output_prefix = "normal_output_file"
        else:
            raise ValueError("Upload mode must be either 'normal' or 'export'.")

        for i, row in df.iterrows():
            self.driver.refresh()
            self._open_sales_page()

            try:
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, f'//button[text()="{upload_button_text}"]'))
                ).click()
            except Exception:
                errors.append("Add New button not clickable")
                invoices.append(str(df["E-Invoice Number"][i]))
                continue

            excel_category = row["Category of Plastic"]
            excel_process = row["Process Code"]
            excel_plastic = row["Plastic Type"]
            excel_product = row["Product"]
            excel_quantity = float(row["Quantity In MT"])

            table_rows = self.driver.find_elements(By.XPATH, '//tbody[@id="ScrollableSimpleTableBody"]/tr')
            for table_row in table_rows:
                category = table_row.find_element(By.XPATH, './td[3]/span').get_attribute('title')
                process = table_row.find_element(By.XPATH, './td[4]/span').get_attribute('title')
                plastic = table_row.find_element(By.XPATH, './td[5]/span').get_attribute('title')
                product = table_row.find_element(By.XPATH, './td[6]/span').get_attribute('title')
                quantity = float(table_row.find_element(By.XPATH, './td[8]/span').get_attribute('title'))

                if (
                    category.strip().lower() == excel_category.strip().lower()
                    and process.strip().lower() == excel_process.strip().lower()
                    and plastic.strip().lower() == excel_plastic.strip().lower()
                    and product.strip().lower() == excel_product.strip().lower()
                    and quantity >= excel_quantity
                ):
                    checkbox = table_row.find_element(By.XPATH, './td[2]/input[@type="checkbox"]')
                    checkbox.click()
                    time.sleep(1)

                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '//input[@name="qty_product_sold"]'))
                    ).send_keys(df["Quantity In MT"][i])

                    time.sleep(2)
                    scroll_element = self.driver.find_element(by=By.XPATH, value='//button[contains(text(),"Generate EPR Invoice Number")]')
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'})",
                        scroll_element,
                    )
                    time.sleep(2)

                    if mode == "normal":
                        try:
                            self.driver.find_element(by=By.XPATH, value='//*[@placeholder="Select Registration Type"]//input').send_keys(df["Registration Type"][i])
                            WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, '//ng-dropdown-panel/div/div[2]/div[1]'))
                            ).click()
                        except Exception:
                            errors.append("registration error")
                            invoices.append(str(df["E-Invoice Number"][i]))
                        time.sleep(2)

                    if str(df["Registration Type"][i]).lower() == "registered":
                        if mode == "normal":
                            try:
                                self.driver.find_element(by=By.XPATH, value='//*[@placeholder="Select Entity Type"]//input').send_keys(df["Entity Type"][i])
                                WebDriverWait(self.driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, '//ng-dropdown-panel/div/div[2]/div[1]'))
                                ).click()
                            except Exception:
                                errors.append("registration error")
                                invoices.append(str(df["E-Invoice Number"][i]))
                            time.sleep(5)

                            try:
                                self.driver.find_element(by=By.XPATH, value='//*[@placeholder="Select Entity Name"]//input').send_keys(df["Name of the Entity"][i])
                                WebDriverWait(self.driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, '//ng-dropdown-panel/div/div[2]/div[1]'))
                                ).click()
                            except Exception:
                                errors.append("registration error")
                                invoices.append(str(df["E-Invoice Number"][i]))
                            time.sleep(2)

                        field_map = [
                            ('//input[@placeholder="Enter GST number"]', df["GST No. of Seller"][i]),
                            ('//input[@placeholder="Enter HSN code"]', df["HSN Code"][i]),
                            ('//input[@placeholder="Enter E-invoice number"]', df["E-Invoice Number"][i]),
                            ('//input[@placeholder="Enter account number"]', df["Bank Account No"][i]),
                            ('//input[@name="ifsc_code"]', df["IFSC Code"][i]),
                            ('//input[@name="amount"]', df["Principal Amount"][i]),
                            ('//input[@name="gst_amount"]', df["GST Amount"][i]),
                        ]
                        if mode == "normal":
                            field_map.insert(1, ('//input[@placeholder="Enter Buyer GST number"]', df["Buyer GST"][i]))

                        for xpath, value in field_map:
                            try:
                                element = self.driver.find_element(by=By.XPATH, value=xpath)
                                element.clear()
                                element.send_keys(value)
                            except Exception:
                                errors.append("registration error")
                                invoices.append(str(df["E-Invoice Number"][i]))
                            time.sleep(1)

                        try:
                            a = str(df["Sales date"][i])[:8]
                            d = f"{a[:4]}-{a[4:6]}-{a[6:]}"
                            date_input = self.driver.find_element(By.XPATH, '//input[@name="salesDate"]')
                            self.driver.execute_script(
                                """
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                                """,
                                date_input,
                                d,
                            )
                        except Exception:
                            errors.append("registration error")
                            invoices.append(str(df["E-Invoice Number"][i]))
                        time.sleep(2)
                    else:
                        non_registered_fields = [
                            ('//*[@placeholder="Entity Name"]', df["Name of the Entity"][i]),
                            ('//input[@name="address"]', df["Address"][i]),
                            ('//input[@placeholder="Enter GST number"]', df["GST No. of Seller"][i]),
                            ('//input[@placeholder="Enter HSN code"]', df["HSN Code"][i]),
                            ('//input[@placeholder="Enter E-invoice number"]', df["E-Invoice Number"][i]),
                            ('//input[@placeholder="Enter account number"]', df["Bank Account No"][i]),
                            ('//input[@name="ifsc_code"]', df["IFSC Code"][i]),
                            ('//input[@name="amount"]', df["Principal Amount"][i]),
                            ('//input[@name="gst_amount"]', df["GST Amount"][i]),
                        ]

                        for xpath, value in non_registered_fields:
                            try:
                                element = self.driver.find_element(by=By.XPATH, value=xpath)
                                element.clear()
                                element.send_keys(value)
                            except Exception:
                                errors.append("registration error")
                                invoices.append(str(df["E-Invoice Number"][i]))
                            time.sleep(1)

                        if mode == "normal":
                            try:
                                self.driver.find_element(by=By.XPATH, value='//*[@name="entity_state_id"]//input').send_keys(df["State"][i])
                                WebDriverWait(self.driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, '//ng-dropdown-panel/div/div[2]/div[1]'))
                                ).click()
                            except Exception:
                                errors.append("registration error")
                                invoices.append(str(df["E-Invoice Number"][i]))
                            time.sleep(2)

                            try:
                                self.driver.find_element(by=By.XPATH, value='//*[@name="entity_district"]//input').send_keys((df["District"][i]).lower().strip())
                                WebDriverWait(self.driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, '//ng-dropdown-panel/div/div[2]/div[1]'))
                                ).click()
                            except Exception:
                                errors.append("registration error")
                                invoices.append(str(df["E-Invoice Number"][i]))
                            time.sleep(2)

                            try:
                                buyer_gst = self.driver.find_element(by=By.XPATH, value='//input[@placeholder="Enter Buyer GST number"]')
                                buyer_gst.clear()
                                buyer_gst.send_keys(df["Buyer GST"][i])
                            except Exception:
                                errors.append("registration error")
                                invoices.append(str(df["E-Invoice Number"][i]))
                            time.sleep(1)

                        try:
                            a = str(df["Sales date"][i])[:8]
                            d = f"{a[:4]}-{a[4:6]}-{a[6:]}"
                            date_input = self.driver.find_element(By.XPATH, '//input[@name="salesDate"]')
                            self.driver.execute_script(
                                """
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                                """,
                                date_input,
                                d,
                            )
                        except Exception:
                            errors.append("registration error")
                            invoices.append(str(df["E-Invoice Number"][i]))
                        time.sleep(2)

                    try:
                        WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(),"Generate EPR Invoice Number")]'))
                        ).click()
                        WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(),"Confirm")]'))
                        ).click()
                        copy_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, '//input[@name="invoice_number"]/following-sibling::button'))
                        )
                        copy_button.click()
                        time.sleep(3)

                        epr_invoice_input = self.driver.find_element(By.XPATH, '//input[@name="invoice_number"]')
                        df.at[i, "EPR Invoice Number"] = epr_invoice_input.get_attribute("value")
                    except Exception:
                        df.at[i, "EPR Invoice Number"] = ""
                    break

        output_file = self.output_dir / f"{output_prefix}_{datetime.datetime.now().strftime('%d%m%Y_%H%M%S')}.xlsx"
        df.to_excel(output_file, index=False)

        payload = {
            "valid": True,
            "message": "Data upload completed.",
            "files": [self.file_payload(output_file)],
            "errors_count": len(errors),
        }
        if errors:
            error_df = pd.DataFrame({"Invoice No": invoices, "Error": errors})
            error_file = self.output_dir / f"data_upload_errors_{self._timestamp()}.xlsx"
            error_df.to_excel(error_file, index=False, engine="openpyxl")
            payload["message"] = "Data upload completed with some errors."
            payload["files"].append(self.file_payload(error_file))
        return payload

    def invoice_upload(self, excel_file_path, pdf_file_paths):
        self._require_login()
        df1 = pd.DataFrame(list(pdf_file_paths), columns=["file_path"])
        df1["file_name"] = df1["file_path"].map(lambda file_path: Path(file_path).stem)
        df = pd.read_excel(excel_file_path, keep_default_na=False, converters={"pdf_filename": str, "Invoice No": str})
        df["pdf_filename"] = df["pdf_filename"].astype(str)
        df["Invoice No"] = df["Invoice No"].astype(str)

        errors = []
        invoices = []
        for i, row in df.iterrows():
            self.driver.refresh()
            self._open_sales_page()
            try:
                self.driver.find_element(by=By.XPATH, value='//*[@placeholder="Search"]').clear()
                self.driver.find_element(by=By.XPATH, value='//*[@placeholder="Search"]').send_keys(df["Invoice No"][i])
                WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[text()="Search"]'))
                ).click()

                matching_row = df1[df1["file_name"] == row["pdf_filename"]]
                if matching_row.empty:
                    raise ValueError(f"No matching PDF found for pdf_filename: {row['pdf_filename']}")

                file_path_for_upload = matching_row.iloc[0]["file_path"]
                time.sleep(2)
                invoice_no = df["Invoice No"][i]
                element = self.driver.find_element(
                    By.XPATH,
                    f'//tbody[@id="ScrollableSimpleTableBody"]/tr[td[7][normalize-space()="{invoice_no}"]]/td[15]/span',
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(1)
                element.click()
                upload_file = self.driver.find_element(by=By.XPATH, value='//*[@name="invoice"]')
                upload_file.send_keys(str(file_path_for_upload))
                time.sleep(2)
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[text()="Upload" and not (@type)]'))
                ).click()
                WebDriverWait(self.driver, 30).until(
                    EC.invisibility_of_element_located((By.XPATH, '//button[text()="Upload" and not (@type)]'))
                )
                time.sleep(5)
            except Exception:
                errors.append("Invoice upload error")
                invoices.append(str(df["Invoice No"][i]))

        payload = {
            "message": "All invoices uploaded successfully.",
            "files": [],
            "errors_count": len(errors),
        }
        if errors:
            error_df = pd.DataFrame({"Invoice No": invoices, "Error": errors})
            error_file = self.output_dir / f"invoice_upload_errors_{self._timestamp()}.xlsx"
            error_df.to_excel(error_file, index=False, engine="openpyxl")
            payload["message"] = "Invoice upload completed with some errors."
            payload["files"].append(self.file_payload(error_file))
        return payload

    def delete_upload_data(self, file_path):
        self._require_login()
        df = pd.read_excel(file_path, converters={"Invoice No": str})
        errors = []
        invoices = []

        for _, row in df.iterrows():
            invoice_no = row["Invoice No"]
            self.driver.refresh()
            self._open_sales_page()
            try:
                search_input = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@placeholder="Search"]'))
                )
                search_input.clear()
                search_input.send_keys(invoice_no)

                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[normalize-space()="Search"]'))
                ).click()

                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//table/tbody/tr"))
                )

                row_xpath = f'//table/tbody/tr[td[7][normalize-space()="{invoice_no}"]]'
                delete_xpath = row_xpath + '//em[contains(@class,"fa-trash")]'
                delete_icon = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, delete_xpath))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", delete_icon)
                self.driver.execute_script("arguments[0].click();", delete_icon)

                confirm = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//div[contains(@class,"confirm_delete")]//button[normalize-space()="Delete"]')
                    )
                )
                self.driver.execute_script("arguments[0].click();", confirm)
            except Exception as exc:
                errors.append(str(exc))
                invoices.append(invoice_no)

        payload = {
            "message": "Delete upload data finished.",
            "files": [],
            "errors_count": len(errors),
        }
        if errors:
            error_df = pd.DataFrame({"Invoice No": invoices, "Error": errors})
            error_file = self.output_dir / f"delete_upload_errors_{self._timestamp()}.xlsx"
            error_df.to_excel(error_file, index=False, engine="openpyxl")
            payload["message"] = "Delete upload completed with some errors."
            payload["files"].append(self.file_payload(error_file))
        return payload

    def scrape_data(self, choice):
        self._require_login()

        def scrape_table(column_indexes, column_names, file_prefix, check_upload=False):
            data_lists = {name: [] for name in column_names}
            if check_upload:
                data_lists["Invoice File Status"] = []

            while True:
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '//tbody[@id="ScrollableSimpleTableBody"]/tr[1]'))
                    )
                    target_element = self.driver.find_element(By.XPATH, '//tbody[@id="ScrollableSimpleTableBody"]/tr[1]')
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target_element)
                except Exception:
                    break

                time.sleep(2)
                tree = html.fromstring(self.driver.page_source)
                rows = tree.xpath('//tbody[@id="ScrollableSimpleTableBody"]/tr')

                row_index = 1
                for row in rows:
                    cells = row.xpath('./td')
                    for col_name, col_index in zip(column_names, column_indexes):
                        data_lists[col_name].append(cells[col_index].text_content() if col_index < len(cells) else "")

                    if check_upload:
                        upload_class = tree.xpath(
                            f'//tbody[@id="ScrollableSimpleTableBody"]/tr[{row_index}]/td[15]/span/@class'
                        )
                        upload_class = upload_class[0] if upload_class else ""
                        data_lists["Invoice File Status"].append("Pending" if "color-red" in upload_class else "Uploaded")
                    row_index += 1

                try:
                    next_button = self.driver.find_element(By.XPATH, '//button[@ngbtooltip="Next"]')
                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable(next_button)).click()
                    time.sleep(5)
                except Exception:
                    break

            filename = self.output_dir / f"{file_prefix}_{datetime.datetime.now().strftime('%d%m%Y_%H%M%S')}.xlsx"
            pd.DataFrame(data_lists).to_excel(filename, index=False)
            return filename

        selected_choice = choice.lower().strip()
        if selected_choice == "procurement":
            file_path = scrape_table(
                column_indexes=[1, 2, 3, 4, 5, 6, 7, 8, 9],
                column_names=[
                    "Name of Supplier",
                    "Address of Supplier",
                    "Categories of Plastic",
                    "Qty. of Waste Plastic (Tons)",
                    "GST No",
                    "Aadhar No",
                    "Mobile No",
                    "Procurement Date",
                    "Date of Entry",
                ],
                file_prefix="procurement_scrap_file",
            )
        elif selected_choice == "production":
            file_path = scrape_table(
                column_indexes=[1, 2, 3, 4, 5, 6, 7, 8],
                column_names=[
                    "Category",
                    "Process Code",
                    "Plastic Type",
                    "Product",
                    "Qty. of Product(Tons)",
                    "Qty. of Input Waste(Tons)",
                    "Percentage of Recycled plastic in product",
                    "Date of Production",
                ],
                file_prefix="production_scrap_file",
            )
        elif selected_choice == "inventory":
            file_path = scrape_table(
                column_indexes=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                column_names=[
                    "Seller GST No",
                    "Total Qty. of Product Sold (Tons)",
                    "Amount(?)",
                    "Date of Sale",
                    "Register Type",
                    "Invoice No",
                    "Name of the Entity",
                    "Address",
                    "District",
                    "State",
                    "Total Potential Generated",
                    "Invoice file",
                ],
                file_prefix="inventory_sales_scrap_file",
                check_upload=True,
            )
        else:
            raise ValueError("Scrape choice must be one of: procurement, production, inventory.")

        return {
            "message": "Scraping completed successfully.",
            "files": [self.file_payload(file_path)],
        }
