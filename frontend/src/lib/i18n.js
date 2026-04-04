"use client";

import { getLanguage } from "./users";

const dict = {
  // ── Common / Shared ──
  back: { English: "Back", Chinese: "返回", Malay: "Kembali", Tamil: "பின்செல்" },
  next: { English: "Next", Chinese: "下一步", Malay: "Seterusnya", Tamil: "அடுத்து" },
  cancel: { English: "Cancel", Chinese: "取消", Malay: "Batal", Tamil: "ரத்து" },
  submit: { English: "Submit", Chinese: "提交", Malay: "Hantar", Tamil: "சமர்ப்பி" },
  save_changes: { English: "Save Changes", Chinese: "保存更改", Malay: "Simpan", Tamil: "மாற்றங்களைச் சேமி" },
  saved: { English: "Saved!", Chinese: "已保存！", Malay: "Disimpan!", Tamil: "சேமிக்கப்பட்டது!" },

  // ── Login ──
  app_name: { English: "The GlucoGardener", Chinese: "The GlucoGardener", Malay: "The GlucoGardener", Tamil: "The GlucoGardener" },
  app_tagline: { English: "Your health companion", Chinese: "您的健康伙伴", Malay: "Teman kesihatan anda", Tamil: "உங்கள் உடல்நல தோழர்" },
  who_is_gardening: { English: "Who is gardening today?", Chinese: "今天谁来照顾花园？", Malay: "Siapa berkebun hari ini?", Tamil: "இன்று யார் தோட்டம் பராமரிக்கிறார்?" },
  watered: { English: "Watered!", Chinese: "已浇水！", Malay: "Disiram!", Tamil: "நீர் ஊற்றப்பட்டது!" },
  no_friends_yet: { English: "No friends yet", Chinese: "暂无好友", Malay: "Belum ada kawan", Tamil: "இன்னும் நண்பர்கள் இல்லை" },
  create_account: { English: "Create New Account", Chinese: "创建新账户", Malay: "Buat Akaun Baru", Tamil: "புதிய கணக்கை உருவாக்கு" },
  sg_innovation: { English: "SG Innovation Challenge 2026", Chinese: "SG Innovation Challenge 2026", Malay: "SG Innovation Challenge 2026", Tamil: "SG Innovation Challenge 2026" },

  // ── Home ──
  good_morning: { English: "Good Morning,", Chinese: "早安，", Malay: "Selamat Pagi,", Tamil: "காலை வணக்கம்," },
  how_feeling: { English: "How are you feeling today?", Chinese: "你今天感觉怎么样？", Malay: "Apa khabar hari ini?", Tamil: "இன்று உங்கள் நிலை எப்படி?" },
  chat_with_ai: { English: ">>Chat with AI", Chinese: ">>和AI聊天", Malay: ">>Sembang dengan AI", Tamil: ">>AI உடன் அரட்டை" },
  todays_snapshot: { English: "Today's Snapshot", Chinese: "今日概览", Malay: "Ringkasan Hari Ini", Tamil: "இன்றைய சுருக்கம்" },
  bmi: { English: "BMI:", Chinese: "BMI:", Malay: "BMI:", Tamil: "BMI:" },
  meals_logged: { English: "Meals logged:", Chinese: "已记录餐数：", Malay: "Makanan dilog:", Tamil: "பதிவான உணவு:" },
  view_tasks: { English: ">>View your tasks", Chinese: ">>查看任务", Malay: ">>Lihat tugas anda", Tamil: ">>உங்கள் பணிகளைக் காண" },
  check_sugar: { English: "Check your sugar", Chinese: "查看血糖", Malay: "Semak gula anda", Tamil: "உங்கள் சர்க்கரையைப் பாருங்கள்" },

  // ── Nav / TopBar ──
  nav_home: { English: "Home", Chinese: "首页", Malay: "Utama", Tamil: "முகப்பு" },
  nav_chat: { English: "Chat", Chinese: "聊天", Malay: "Sembang", Tamil: "அரட்டை" },
  nav_task: { English: "Task", Chinese: "任务", Malay: "Tugas", Tamil: "பணி" },
  nav_garden: { English: "Garden", Chinese: "花园", Malay: "Taman", Tamil: "தோட்டம்" },
  nav_setting: { English: "Setting", Chinese: "设置", Malay: "Tetapan", Tamil: "அமைப்புகள்" },
  nav_soft_alert: { English: "Soft Alert", Chinese: "温和提醒", Malay: "Amaran Lembut", Tamil: "மென் எச்சரிக்கை" },
  nav_hard_alert: { English: "Hard Alert", Chinese: "紧急提醒", Malay: "Amaran Keras", Tamil: "கடும் எச்சரிக்கை" },

  // ── Chat ──
  recording: { English: "Recording...", Chinese: "录音中...", Malay: "Merakam...", Tamil: "பதிவு செய்கிறது..." },
  chat_error: { English: "Sorry, something went wrong. Please try again.", Chinese: "抱歉，出了点问题。请重试。", Malay: "Maaf, ada masalah. Sila cuba lagi.", Tamil: "மன்னிக்கவும், பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்." },
  type_message: { English: "Type a message...", Chinese: "输入消息...", Malay: "Taip mesej...", Tamil: "செய்தி தட்டச்சு..." },

  // ── Task ──
  task_title: { English: "Task", Chinese: "任务", Malay: "Tugas", Tamil: "பணி" },
  task_log_meals: { English: "Log your meals", Chinese: "记录饮食", Malay: "Log makanan anda", Tamil: "உணவைப் பதிவு செய்" },
  task_log_meals_desc: { English: "Small notes today, better insights tomorrow.", Chinese: "今天的小记录，明天的大洞察。", Malay: "Nota kecil hari ini, pandangan lebih baik esok.", Tamil: "இன்றைய சிறு குறிப்புகள், நாளைய சிறந்த நுண்ணறிவுகள்." },
  task_meal_logged: { English: "Meal Logged!", Chinese: "已记录！", Malay: "Makanan Dilog!", Tamil: "உணவு பதிவு!" },
  task_body_checkin: { English: "Body check-in", Chinese: "身体记录", Malay: "Pemeriksaan badan", Tamil: "உடல் பதிவு" },
  task_body_checkin_desc: { English: "Tracking your waist helps monitor metabolic health.", Chinese: "追踪腰围有助于监测代谢健康。", Malay: "Menjejak pinggang membantu memantau kesihatan metabolik.", Tamil: "இடுப்பை கண்காணிப்பது வளர்சிதை மாற்ற ஆரோக்கியத்தை கண்காணிக்க உதவுகிறது." },
  task_checked_in: { English: "Checked In!", Chinese: "已记录！", Malay: "Daftar Masuk!", Tamil: "பதிவு செய்யப்பட்டது!" },
  task_sunset: { English: "Sunset chaser", Chinese: "追逐日落", Malay: "Pengejar matahari terbenam", Tamil: "சூரிய அஸ்தமன வேட்டை" },
  task_sunset_desc: { English: "Personalised quest: Take a brisk walk at West Coast Park and capture the sunset.", Chinese: "个性化任务：在西海岸公园快走，捕捉日落。", Malay: "Cabaran peribadi: Berjalan pantas di West Coast Park dan tangkap matahari terbenam.", Tamil: "தனிப்பயன் சவால்: West Coast Park-ல் வேகமாக நடந்து சூரிய அஸ்தமனத்தைப் படமெடுங்கள்." },
  task_logged: { English: "Logged!", Chinese: "已记录！", Malay: "Dilog!", Tamil: "பதிவு!" },
  task_log_here: { English: "Log Here", Chinese: "记录", Malay: "Log Sini", Tamil: "இங்கே பதிவு" },
  task_daily_completed: { English: "Daily task completed", Chinese: "每日任务完成", Malay: "Tugas harian selesai", Tamil: "தினசரி பணி நிறைவு" },
  task_plant_progress: { English: "Plant growth progress", Chinese: "植物成长进度", Malay: "Kemajuan pertumbuhan pokok", Tamil: "தாவர வளர்ச்சி முன்னேற்றம்" },
  task_total_pts: { English: "Total pts", Chinese: "总积分", Malay: "Jumlah mata", Tamil: "மொத்த புள்ளிகள்" },
  task_pts: { English: "pts", Chinese: "分", Malay: "mata", Tamil: "புள்ளிகள்" },
  task_pt_earned: { English: "pt earned!", Chinese: "分已获得！", Malay: "mata diperoleh!", Tamil: "புள்ளி பெறப்பட்டது!" },
  upload: { English: "Upload", Chinese: "上传", Malay: "Muat naik", Tamil: "பதிவேற்று" },
  open_camera: { English: "Open Camera", Chinese: "打开相机", Malay: "Buka Kamera", Tamil: "கேமரா திற" },
  open_gallery: { English: "Open Gallery", Chinese: "打开相册", Malay: "Buka Galeri", Tamil: "கேலரி திற" },
  body_checkin_title: { English: "Body Check-in", Chinese: "身体记录", Malay: "Pemeriksaan Badan", Tamil: "உடல் பதிவு" },
  waist_cm: { English: "Current Waist (cm)", Chinese: "当前腰围（厘米）", Malay: "Pinggang Semasa (cm)", Tamil: "தற்போதைய இடுப்பு (செமீ)" },
  weight_kg: { English: "Current Weight (kg)", Chinese: "当前体重（公斤）", Malay: "Berat Semasa (kg)", Tamil: "தற்போதைய எடை (கிகி)" },

  // ── Garden ──
  garden_title: { English: "Garden", Chinese: "花园", Malay: "Taman", Tamil: "தோட்டம்" },
  friends: { English: "Friends", Chinese: "好友", Malay: "Rakan", Tamil: "நண்பர்கள்" },
  visit: { English: "Visit>>", Chinese: "访问>>", Malay: "Lawat>>", Tamil: "வருகை>>" },
  garden_of: { English: "'s Garden", Chinese: "的花园", Malay: " Taman", Tamil: " தோட்டம்" },
  points: { English: "points", Chinese: "积分", Malay: "mata", Tamil: "புள்ளிகள்" },
  water_garden: { English: "Water their garden (+10 pts)", Chinese: "浇水 (+10 积分)", Malay: "Siram taman mereka (+10 mata)", Tamil: "தோட்டத்தை நீர் ஊற்று (+10 புள்ளிகள்)" },
  visit_once_per_day: { English: "You can visit once per day", Chinese: "每天可以访问一次", Malay: "Anda boleh melawat sekali sehari", Tamil: "நாளுக்கு ஒரு முறை வருகை தர முடியும்" },
  visited_garden: { English: "You visited {name}'s garden! +10 points", Chinese: "你访问了{name}的花园！+10积分", Malay: "Anda melawat taman {name}! +10 mata", Tamil: "நீங்கள் {name} தோட்டத்திற்கு வருகை தந்தீர்கள்! +10 புள்ளிகள்" },

  // ── Settings ──
  setting_title: { English: "Setting", Chinese: "设置", Malay: "Tetapan", Tamil: "அமைப்புகள்" },
  account: { English: "Account", Chinese: "账户", Malay: "Akaun", Tamil: "கணக்கு" },
  change_language: { English: "Change Language", Chinese: "更改语言", Malay: "Tukar Bahasa", Tamil: "மொழி மாற்று" },
  terms_conditions: { English: "Terms & Conditions", Chinese: "条款与条件", Malay: "Terma & Syarat", Tamil: "விதிமுறைகள்" },
  privacy_policy: { English: "Privacy Policy", Chinese: "隐私政策", Malay: "Dasar Privasi", Tamil: "தனியுரிமைக் கொள்கை" },
  about: { English: "About", Chinese: "关于", Malay: "Tentang", Tamil: "பற்றி" },
  logout: { English: "Logout", Chinese: "退出登录", Malay: "Log Keluar", Tamil: "வெளியேறு" },

  // ── Account ──
  tap_change_avatar: { English: "Tap to change avatar", Chinese: "点击更换头像", Malay: "Ketik untuk tukar avatar", Tamil: "அவதாரத்தை மாற்ற தட்டவும்" },
  change: { English: "Change", Chinese: "更换", Malay: "Tukar", Tamil: "மாற்று" },
  choose_avatar: { English: "Choose Avatar", Chinese: "选择头像", Malay: "Pilih Avatar", Tamil: "அவதாரத்தைத் தேர்ந்தெடு" },
  personal_info: { English: "Personal Info", Chinese: "个人信息", Malay: "Maklumat Peribadi", Tamil: "தனிப்பட்ட தகவல்" },
  name: { English: "Name", Chinese: "姓名", Malay: "Nama", Tamil: "பெயர்" },
  birth_year: { English: "Birth Year", Chinese: "出生年份", Malay: "Tahun Lahir", Tamil: "பிறந்த ஆண்டு" },
  gender: { English: "Gender", Chinese: "性别", Malay: "Jantina", Tamil: "பாலினம்" },
  male: { English: "Male", Chinese: "男", Malay: "Lelaki", Tamil: "ஆண்" },
  female: { English: "Female", Chinese: "女", Malay: "Perempuan", Tamil: "பெண்" },
  other: { English: "Other", Chinese: "其他", Malay: "Lain-lain", Tamil: "மற்றவை" },
  health_info: { English: "Health Info", Chinese: "健康信息", Malay: "Maklumat Kesihatan", Tamil: "சுகாதார தகவல்" },
  height_cm: { English: "Height (cm)", Chinese: "身高（厘米）", Malay: "Tinggi (cm)", Tamil: "உயரம் (செமீ)" },
  bmi_auto: { English: "BMI (auto-calculated)", Chinese: "BMI（自动计算）", Malay: "BMI (pengiraan automatik)", Tamil: "BMI (தானியங்கி கணக்கீடு)" },

  // ── Account — Weekly Exercise ──
  weekly_exercise: { English: "Weekly Exercise Plan", Chinese: "每周运动计划", Malay: "Pelan Senaman Mingguan", Tamil: "வாராந்திர உடற்பயிற்சி திட்டம்" },
  add_schedule: { English: "+ Add Schedule", Chinese: "+ 添加计划", Malay: "+ Tambah Jadual", Tamil: "+ அட்டவணை சேர்" },
  day_of_week: { English: "Day", Chinese: "星期", Malay: "Hari", Tamil: "நாள்" },
  start_time: { English: "Start", Chinese: "开始", Malay: "Mula", Tamil: "தொடக்கம்" },
  end_time: { English: "End", Chinese: "结束", Malay: "Tamat", Tamil: "முடிவு" },
  activity_type: { English: "Type", Chinese: "类型", Malay: "Jenis", Tamil: "வகை" },
  resistance_training: { English: "Resistance Training", Chinese: "力量训练", Malay: "Latihan Rintangan", Tamil: "எதிர்ப்பு பயிற்சி" },
  cardio: { English: "Cardio", Chinese: "有氧运动", Malay: "Kardio", Tamil: "இதய பயிற்சி" },
  hiit: { English: "HIIT", Chinese: "高强度间歇", Malay: "HIIT", Tamil: "HIIT" },
  monday: { English: "Monday", Chinese: "周一", Malay: "Isnin", Tamil: "திங்கள்" },
  tuesday: { English: "Tuesday", Chinese: "周二", Malay: "Selasa", Tamil: "செவ்வாய்" },
  wednesday: { English: "Wednesday", Chinese: "周三", Malay: "Rabu", Tamil: "புதன்" },
  thursday: { English: "Thursday", Chinese: "周四", Malay: "Khamis", Tamil: "வியாழன்" },
  friday: { English: "Friday", Chinese: "周五", Malay: "Jumaat", Tamil: "வெள்ளி" },
  saturday: { English: "Saturday", Chinese: "周六", Malay: "Sabtu", Tamil: "சனி" },
  sunday: { English: "Sunday", Chinese: "周日", Malay: "Ahad", Tamil: "ஞாயிறு" },

  // ── Account — Known Places ──
  known_places: { English: "Known Places", Chinese: "已知地点", Malay: "Tempat Diketahui", Tamil: "அறியப்பட்ட இடங்கள்" },
  add_place: { English: "+ Add Place", Chinese: "+ 添加地点", Malay: "+ Tambah Tempat", Tamil: "+ இடம் சேர்" },
  place_name: { English: "Place Name", Chinese: "地点名称", Malay: "Nama Tempat", Tamil: "இடத்தின் பெயர்" },
  place_type: { English: "Type", Chinese: "类型", Malay: "Jenis", Tamil: "வகை" },
  place_home: { English: "Home", Chinese: "家", Malay: "Rumah", Tamil: "வீடு" },
  place_gym: { English: "Gym", Chinese: "健身房", Malay: "Gim", Tamil: "உடற்பயிற்சி கூடம்" },
  place_office: { English: "Office", Chinese: "办公室", Malay: "Pejabat", Tamil: "அலுவலகம்" },
  gps_lat: { English: "Latitude", Chinese: "纬度", Malay: "Latitud", Tamil: "அட்சரேகை" },
  gps_lng: { English: "Longitude", Chinese: "经度", Malay: "Longitud", Tamil: "தீர்க்கரேகை" },

  // ── Account — Emergency Contacts ──
  emergency_contacts: { English: "Emergency Contacts", Chinese: "紧急联系人", Malay: "Hubungan Kecemasan", Tamil: "அவசர தொடர்புகள்" },
  add_contact: { English: "+ Add Contact", Chinese: "+ 添加联系人", Malay: "+ Tambah Kenalan", Tamil: "+ தொடர்பு சேர்" },
  contact_name: { English: "Name", Chinese: "姓名", Malay: "Nama", Tamil: "பெயர்" },
  phone_number: { English: "Phone", Chinese: "电话", Malay: "Telefon", Tamil: "தொலைபேசி" },
  relationship: { English: "Relationship", Chinese: "关系", Malay: "Hubungan", Tamil: "உறவு" },
  rel_family: { English: "Family", Chinese: "家人", Malay: "Keluarga", Tamil: "குடும்பம்" },
  rel_friend: { English: "Friend", Chinese: "朋友", Malay: "Kawan", Tamil: "நண்பர்" },
  rel_doctor: { English: "Doctor", Chinese: "医生", Malay: "Doktor", Tamil: "மருத்துவர்" },
  notify_on: { English: "Notify On", Chinese: "通知类型", Malay: "Maklumkan Apabila", Tamil: "அறிவிப்பு வகை" },
  hard_low_glucose: { English: "Low Glucose", Chinese: "低血糖", Malay: "Glukosa Rendah", Tamil: "குறைந்த குளுக்கோஸ்" },
  hard_high_hr: { English: "High Heart Rate", Chinese: "高心率", Malay: "Kadar Jantung Tinggi", Tamil: "அதிக இதயத் துடிப்பு" },
  data_gap: { English: "Data Gap", Chinese: "数据中断", Malay: "Jurang Data", Tamil: "தரவு இடைவெளி" },
  remove: { English: "Remove", Chinese: "删除", Malay: "Buang", Tamil: "நீக்கு" },

  // ── Language page ──
  choose_language: { English: "Choose your preferred language", Chinese: "选择您的首选语言", Malay: "Pilih bahasa pilihan anda", Tamil: "உங்கள் விருப்ப மொழியைத் தேர்ந்தெடுக்கவும்" },
  language_applied: { English: "Language setting will be applied across the app", Chinese: "语言设置将应用于整个应用", Malay: "Tetapan bahasa akan digunakan di seluruh aplikasi", Tamil: "மொழி அமைப்பு முழு பயன்பாட்டிலும் பொருந்தும்" },

  // ── Onboarding ──
  welcome_title: { English: "Welcome to\nThe GlucoGardener!", Chinese: "欢迎来到\nThe GlucoGardener！", Malay: "Selamat Datang ke\nThe GlucoGardener!", Tamil: "The GlucoGardener-க்கு\nவரவேற்கிறோம்!" },
  setup_profile: { English: "Let's set up your profile", Chinese: "让我们设置你的个人资料", Malay: "Mari sediakan profil anda", Tamil: "உங்கள் சுயவிவரத்தை அமைப்போம்" },
  choose_avatar_prompt: { English: "Choose your avatar", Chinese: "选择你的头像", Malay: "Pilih avatar anda", Tamil: "உங்கள் அவதாரத்தைத் தேர்ந்தெடுங்கள்" },
  tell_about_you: { English: "Tell us about you", Chinese: "告诉我们关于你的信息", Malay: "Ceritakan tentang anda", Tamil: "உங்களைப் பற்றி சொல்லுங்கள்" },
  personalise_experience: { English: "This helps us personalise your experience", Chinese: "这有助于我们为您提供个性化体验", Malay: "Ini membantu kami memperibadikan pengalaman anda", Tamil: "இது உங்கள் அனுபவத்தைத் தனிப்பயனாக்க உதவுகிறது" },
  select_placeholder: { English: "Select...", Chinese: "请选择...", Malay: "Pilih...", Tamil: "தேர்ந்தெடு..." },
  health_profile: { English: "Your health profile", Chinese: "你的健康档案", Malay: "Profil kesihatan anda", Tamil: "உங்கள் சுகாதார சுயவிவரம்" },
  better_insights: { English: "We use this to give you better insights", Chinese: "我们用这些数据为您提供更好的健康建议", Malay: "Kami gunakan ini untuk memberi pandangan lebih baik", Tamil: "சிறந்த நுண்ணறிவை வழங்க இதைப் பயன்படுத்துகிறோம்" },
  waist_circumference: { English: "Current Waist circumference (cm)", Chinese: "当前腰围（厘米）", Malay: "Lilitan pinggang semasa (cm)", Tamil: "தற்போதைய இடுப்பு சுற்றளவு (செமீ)" },
  choose_your_language: { English: "Choose your language", Chinese: "选择你的语言", Malay: "Pilih bahasa anda", Tamil: "உங்கள் மொழியைத் தேர்ந்தெடுங்கள்" },
  change_later_settings: { English: "You can change this later in Settings", Chinese: "你可以稍后在设置中更改", Malay: "Anda boleh tukar kemudian di Tetapan", Tamil: "பின்னர் அமைப்புகளில் மாற்றலாம்" },
  all_set: { English: "All set!", Chinese: "准备就绪！", Malay: "Sedia!", Tamil: "தயார்!" },
  garden_ready: { English: "Your garden is ready to grow.", Chinese: "你的花园准备好成长了。", Malay: "Taman anda sedia untuk berkembang.", Tamil: "உங்கள் தோட்டம் வளர தயாராக உள்ளது." },
  complete_tasks_bloom: { English: "Complete daily tasks to earn points and watch your garden bloom", Chinese: "完成每日任务赚取积分，看你的花园绽放", Malay: "Selesaikan tugas harian untuk mendapat mata dan lihat taman anda mekar", Tamil: "தினசரி பணிகளை நிறைவு செய்து புள்ளிகள் பெற்று தோட்டம் பூக்கட்டும்" },
  start_gardening: { English: "Start Gardening", Chinese: "开始种花", Malay: "Mula Berkebun", Tamil: "தோட்டம் தொடங்கு" },

  // ── Soft Alert ──
  heads_up: { English: "Heads up!", Chinese: "注意！", Malay: "Perhatian!", Tamil: "கவனம்!" },
  soft_alert_msg: {
    English: "Your glucose is 4.9 mmol/L. If you start resistance training, it could drop to 4.04 mmol/L. Consider a small apple or handful of nuts (15-30g slow-release carbs) beforehand. Stay safe and strong!",
    Chinese: "您的血糖是 4.9 mmol/L。如果您开始力量训练，血糖可能降至 4.04 mmol/L。建议先吃一个小苹果或一把坚果（15-30克缓释碳水）。注意安全！",
    Malay: "Glukosa anda 4.9 mmol/L. Jika anda mula latihan rintangan, ia boleh turun ke 4.04 mmol/L. Pertimbangkan epal kecil atau segenggam kacang (15-30g karbohidrat lepasan perlahan) sebelumnya. Kekal selamat!",
    Tamil: "உங்கள் குளுக்கோஸ் 4.9 mmol/L. நீங்கள் எதிர்ப்பு பயிற்சி தொடங்கினால், 4.04 mmol/L ஆகக் குறையலாம். முன்கூட்டியே ஒரு சிறிய ஆப்பிள் அல்லது ஒரு கைப்பிடி கொட்டைகள் (15-30g மெதுவாக வெளியிடும் கார்ப்ஸ்) சாப்பிடுங்கள்.",
  },

  // ── Hard Alert ──
  alert_hypo: { English: "Alert! Potential Hypoglycemia", Chinese: "警报！可能发生低血糖", Malay: "Amaran! Potensi Hipoglisemia", Tamil: "எச்சரிக்கை! சாத்தியமான இரத்தச் சர்க்கரைக் குறைவு" },
  alert_hypo_msg: {
    English: "Your blood sugar level appears to be low. Please consider having a quick source of sugar and check your level again.",
    Chinese: "您的血糖水平似乎偏低。请考虑补充快速糖分来源，然后再次检查您的血糖水平。",
    Malay: "Paras gula darah anda nampaknya rendah. Sila pertimbangkan untuk mengambil sumber gula cepat dan semak paras anda semula.",
    Tamil: "உங்கள் இரத்த சர்க்கரை அளவு குறைவாக உள்ளது. விரைவான சர்க்கரை ஆதாரத்தை எடுத்துக்கொண்டு மீண்டும் சோதிக்கவும்.",
  },

  // ── Sugar Chart ──
  blood: { English: "Blood", Chinese: "血糖", Malay: "Gula", Tamil: "இரத்த" },
  sugar: { English: "sugar", Chinese: "", Malay: "darah", Tamil: "சர்க்கரை" },
  now: { English: "Now", Chinese: "现在", Malay: "Sekarang", Tamil: "இப்போது" },

  // ── Terms (long text) ──
  terms_heading: { English: "Terms & Conditions", Chinese: "条款与条件", Malay: "Terma & Syarat", Tamil: "விதிமுறைகள் & நிபந்தனைகள்" },
  terms_intro: {
    English: "Welcome to The GlucoGardener. By using this application, you agree to the following terms and conditions.",
    Chinese: "欢迎使用 The GlucoGardener。使用本应用即表示您同意以下条款与条件。",
    Malay: "Selamat datang ke The GlucoGardener. Dengan menggunakan aplikasi ini, anda bersetuju dengan terma dan syarat berikut.",
    Tamil: "The GlucoGardener-க்கு வரவேற்கிறோம். இந்த பயன்பாட்டைப் பயன்படுத்துவதன் மூலம், பின்வரும் விதிமுறைகளை ஏற்கிறீர்கள்.",
  },
  terms_purpose_title: { English: "1. Purpose.", Chinese: "1. 目的。", Malay: "1. Tujuan.", Tamil: "1. நோக்கம்." },
  terms_purpose: {
    English: "This application is designed as a health companion tool for diabetes management. It is not a substitute for professional medical advice, diagnosis, or treatment.",
    Chinese: "本应用是为糖尿病管理设计的健康伴侣工具。它不能替代专业的医疗建议、诊断或治疗。",
    Malay: "Aplikasi ini direka sebagai alat kesihatan untuk pengurusan diabetes. Ia bukan pengganti nasihat perubatan profesional.",
    Tamil: "இந்த பயன்பாடு நீரிழிவு மேலாண்மைக்கான உடல்நல துணைக் கருவி. இது தொழில்முறை மருத்துவ ஆலோசனைக்கு மாற்றாகாது.",
  },
  terms_data_title: { English: "2. Data Collection.", Chinese: "2. 数据收集。", Malay: "2. Pengumpulan Data.", Tamil: "2. தரவு சேகரிப்பு." },
  terms_data: {
    English: "We collect health-related data including glucose readings, dietary information, and activity data to provide personalised recommendations.",
    Chinese: "我们收集健康相关数据，包括血糖读数、饮食信息和活动数据，以提供个性化建议。",
    Malay: "Kami mengumpul data berkaitan kesihatan termasuk bacaan glukosa, maklumat diet, dan data aktiviti untuk cadangan yang diperibadikan.",
    Tamil: "தனிப்பயனாக்கப்பட்ட பரிந்துரைகளை வழங்க குளுக்கோஸ் அளவீடுகள், உணவுத் தகவல்கள் மற்றும் செயல்பாட்டுத் தரவு உள்ளிட்ட சுகாதார தொடர்பான தரவை நாங்கள் சேகரிக்கிறோம்.",
  },
  terms_user_title: { English: "3. User Responsibility.", Chinese: "3. 用户责任。", Malay: "3. Tanggungjawab Pengguna.", Tamil: "3. பயனர் பொறுப்பு." },
  terms_user: {
    English: "Users are responsible for the accuracy of self-reported data. Always consult your healthcare provider for medical decisions.",
    Chinese: "用户对自行报告数据的准确性负责。请始终咨询您的医疗保健提供者做出医疗决定。",
    Malay: "Pengguna bertanggungjawab atas ketepatan data yang dilaporkan sendiri. Sentiasa rujuk penyedia penjagaan kesihatan anda.",
    Tamil: "சுய-அறிக்கையிடப்பட்ட தரவின் துல்லியத்திற்கு பயனர்கள் பொறுப்பு. மருத்துவ முடிவுகளுக்கு எப்போதும் உங்கள் சுகாதார வழங்குநரை ஆலோசிக்கவும்.",
  },
  terms_disclaimer_title: { English: "4. Disclaimer.", Chinese: "4. 免责声明。", Malay: "4. Penafian.", Tamil: "4. பொறுப்புத் துறப்பு." },
  terms_disclaimer: {
    English: "The AI-generated advice provided by this application is for informational purposes only and should not replace professional medical guidance.",
    Chinese: "本应用提供的AI生成建议仅供参考，不应取代专业医疗指导。",
    Malay: "Nasihat yang dijana AI oleh aplikasi ini adalah untuk tujuan maklumat sahaja dan tidak seharusnya menggantikan panduan perubatan profesional.",
    Tamil: "இந்த பயன்பாட்டால் வழங்கப்படும் AI ஆலோசனை தகவல் நோக்கங்களுக்காக மட்டுமே, தொழில்முறை மருத்துவ வழிகாட்டுதலுக்கு மாற்றாகாது.",
  },
  last_updated: { English: "Last updated: April 2026", Chinese: "最后更新：2026年4月", Malay: "Kemas kini terakhir: April 2026", Tamil: "கடைசி புதுப்பிப்பு: ஏப்ரல் 2026" },

  // ── Privacy ──
  privacy_heading: { English: "Privacy Policy", Chinese: "隐私政策", Malay: "Dasar Privasi", Tamil: "தனியுரிமைக் கொள்கை" },
  privacy_intro: {
    English: "The GlucoGardener is committed to protecting your privacy and personal health data.",
    Chinese: "The GlucoGardener 致力于保护您的隐私和个人健康数据。",
    Malay: "The GlucoGardener komited untuk melindungi privasi dan data kesihatan peribadi anda.",
    Tamil: "The GlucoGardener உங்கள் தனியுரிமை மற்றும் தனிப்பட்ட சுகாதார தரவைப் பாதுகாக்க உறுதிபூண்டுள்ளது.",
  },
  privacy_collect_title: { English: "Data We Collect.", Chinese: "我们收集的数据。", Malay: "Data Yang Kami Kumpul.", Tamil: "நாங்கள் சேகரிக்கும் தரவு." },
  privacy_collect: {
    English: "Health metrics (glucose levels, heart rate), dietary logs, exercise data, and conversation history with the AI companion.",
    Chinese: "健康指标（血糖水平、心率）、饮食日志、运动数据以及与AI伙伴的对话历史。",
    Malay: "Metrik kesihatan (paras glukosa, kadar jantung), log diet, data senaman, dan sejarah perbualan dengan AI.",
    Tamil: "சுகாதார அளவீடுகள் (குளுக்கோஸ், இதயத் துடிப்பு), உணவுப் பதிவுகள், உடற்பயிற்சித் தரவு மற்றும் AI உடனான உரையாடல் வரலாறு.",
  },
  privacy_use_title: { English: "How We Use It.", Chinese: "我们如何使用。", Malay: "Cara Kami Gunakan.", Tamil: "நாங்கள் எவ்வாறு பயன்படுத்துகிறோம்." },
  privacy_use: {
    English: "Your data is used solely to provide personalised health insights, task recommendations, and alert notifications. We do not sell or share your data with third parties.",
    Chinese: "您的数据仅用于提供个性化健康见解、任务推荐和警报通知。我们不会出售或与第三方共享您的数据。",
    Malay: "Data anda hanya digunakan untuk pandangan kesihatan yang diperibadikan, cadangan tugas, dan pemberitahuan amaran. Kami tidak menjual atau berkongsi data anda.",
    Tamil: "உங்கள் தரவு தனிப்பயனாக்கப்பட்ட சுகாதார நுண்ணறிவுகள், பணி பரிந்துரைகள் மற்றும் எச்சரிக்கை அறிவிப்புகளை வழங்க மட்டுமே பயன்படுத்தப்படுகிறது.",
  },
  privacy_storage_title: { English: "Data Storage.", Chinese: "数据存储。", Malay: "Penyimpanan Data.", Tamil: "தரவு சேமிப்பு." },
  privacy_storage: {
    English: "All data is securely stored in encrypted databases. You may request deletion of your data at any time.",
    Chinese: "所有数据安全存储在加密数据库中。您可以随时要求删除您的数据。",
    Malay: "Semua data disimpan dengan selamat dalam pangkalan data yang disulitkan. Anda boleh meminta pemadaman data pada bila-bila masa.",
    Tamil: "அனைத்து தரவும் குறியாக்கப்பட்ட தரவுத்தளங்களில் பாதுகாப்பாக சேமிக்கப்படுகிறது. எந்த நேரத்திலும் உங்கள் தரவை நீக்கக் கோரலாம்.",
  },
  privacy_clinician_title: { English: "Clinician Access.", Chinese: "医生访问。", Malay: "Akses Klinikan.", Tamil: "மருத்துவர் அணுகல்." },
  privacy_clinician: {
    English: "Aggregated, anonymized health summaries may be shared with your designated healthcare provider to support clinical decisions.",
    Chinese: "汇总的匿名健康摘要可能会与您指定的医疗保健提供者共享，以支持临床决策。",
    Malay: "Ringkasan kesihatan agregat dan tanpa nama boleh dikongsi dengan penyedia penjagaan kesihatan anda untuk menyokong keputusan klinikal.",
    Tamil: "ஒருங்கிணைக்கப்பட்ட, அநாமதேய சுகாதார சுருக்கங்கள் மருத்துவ முடிவுகளை ஆதரிக்க உங்கள் நியமிக்கப்பட்ட சுகாதார வழங்குநருடன் பகிரப்படலாம்.",
  },

  // ── About ──
  about_heading: { English: "The GlucoGardener", Chinese: "The GlucoGardener", Malay: "The GlucoGardener", Tamil: "The GlucoGardener" },
  version: { English: "Version 1.0.0", Chinese: "版本 1.0.0", Malay: "Versi 1.0.0", Tamil: "பதிப்பு 1.0.0" },
  about_desc1: {
    English: "An AI-powered chronic disease management platform for Type 2 diabetes patients in Singapore.",
    Chinese: "面向新加坡2型糖尿病患者的AI慢性病管理平台。",
    Malay: "Platform pengurusan penyakit kronik berkuasa AI untuk pesakit diabetes Jenis 2 di Singapura.",
    Tamil: "சிங்கப்பூரில் வகை 2 நீரிழிவு நோயாளிகளுக்கான AI இயங்கும் நாள்பட்ட நோய் மேலாண்மை தளம்.",
  },
  about_desc2: {
    English: "The GlucoGardener combines a multimodal health companion chatbot, personalised task management, two-tier risk alerts, and gamified health tracking to support patients in their daily diabetes management journey.",
    Chinese: "The GlucoGardener 结合了多模态健康伴侣聊天机器人、个性化任务管理、双层风险警报和游戏化健康追踪，支持患者的日常糖尿病管理。",
    Malay: "The GlucoGardener menggabungkan chatbot kesihatan multimodal, pengurusan tugas yang diperibadikan, amaran risiko dua peringkat, dan penjejakan kesihatan bergamifikasi.",
    Tamil: "The GlucoGardener பலமுறை சுகாதார தோழர் chatbot, தனிப்பயனாக்கப்பட்ட பணி மேலாண்மை, இரு-அடுக்கு ஆபத்து எச்சரிக்கைகள் மற்றும் விளையாட்டுமயமாக்கப்பட்ட சுகாதார கண்காணிப்பை ஒருங்கிணைக்கிறது.",
  },
  team: { English: "Team AAAMedMaster", Chinese: "AAAMedMaster 团队", Malay: "Pasukan AAAMedMaster", Tamil: "குழு AAAMedMaster" },
  built_for: {
    English: "Built for the NUS-SYNAPXE-IMDA AI Innovation Challenge 2026.",
    Chinese: "为 NUS-SYNAPXE-IMDA AI 创新挑战赛 2026 而建。",
    Malay: "Dibina untuk NUS-SYNAPXE-IMDA AI Innovation Challenge 2026.",
    Tamil: "NUS-SYNAPXE-IMDA AI Innovation Challenge 2026-க்காக உருவாக்கப்பட்டது.",
  },
  acknowledgements: { English: "Acknowledgements", Chinese: "致谢", Malay: "Penghargaan", Tamil: "நன்றி" },
  ack_text: {
    English: "We gratefully acknowledge AISG for SEA-LION and MERaLiON model support, and IMDA for mentorship guidance.",
    Chinese: "我们衷心感谢 AISG 提供的 SEA-LION 和 MERaLiON 模型支持，以及 IMDA 的导师指导。",
    Malay: "Kami mengucapkan terima kasih kepada AISG atas sokongan model SEA-LION dan MERaLiON, serta IMDA atas bimbingan mentor.",
    Tamil: "SEA-LION மற்றும் MERaLiON மாதிரி ஆதரவுக்கு AISG-க்கும், வழிகாட்டுதலுக்கு IMDA-க்கும் நன்றி தெரிவிக்கிறோம்.",
  },
};

export function useTranslation() {
  const lang = getLanguage();

  function t(key, replacements) {
    const entry = dict[key];
    if (!entry) return key;
    let text = entry[lang] || entry["English"] || key;
    if (replacements) {
      Object.entries(replacements).forEach(([k, v]) => {
        text = text.replace(`{${k}}`, v);
      });
    }
    return text;
  }

  return { t, lang };
}
