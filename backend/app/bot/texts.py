"""All bot copy in Marathi, Hindi and English (Chapter 7). One source of truth.

Usage: t(lang, "key", **kwargs) -> formatted string, with mr -> en -> key fallback.
"""
from __future__ import annotations

LANGUAGES: dict[str, str] = {"mr": "मराठी", "hi": "हिंदी", "en": "English"}

TEXTS: dict[str, dict[str, str]] = {
    "mr": {
        "choose_language": "🙏 नमस्कार! Job Alert Bot मध्ये स्वागत आहे.\n\nतुमची भाषा निवडा / Choose your language:",
        "ask_name": "👤 तुमचं पूर्ण नाव टाईप करा\nउदा. राहुल सुरेश पाटील",
        "bad_name": "⚠️ कृपया योग्य पूर्ण नाव लिहा (किमान 2 शब्द, फक्त अक्षरे).",
        "ask_phone": "📱 खालील बटण दाबून तुमचा मोबाईल नंबर शेअर करा.\nनंबर टाईप करायची गरज नाही.",
        "share_phone_btn": "📱 नंबर शेअर करा",
        "phone_not_own": "⚠️ कृपया स्वतःचा नंबर शेअर करा, खालील बटण वापरून.",
        "use_button": "👇 कृपया खालील बटण वापरा.",
        "ask_district": "📍 तुमचा जिल्हा निवडा किंवा टाईप करा:",
        "other_district_btn": "✍️ दुसरा जिल्हा",
        "type_district": "✍️ तुमच्या जिल्ह्याचं नाव टाईप करा:",
        "ask_resume": "📄 तुमचा Resume पाठवा\nPDF, Word (DOCX) किंवा resume चा स्पष्ट फोटो चालेल.",
        "no_resume_btn": "❌ माझ्याकडे resume नाही",
        "resume_checking": "⏳ Resume तपासत आहे... 10-20 सेकंद लागतील.",
        "resume_bad_file": "⚠️ ही फाईल चालणार नाही. PDF, DOCX किंवा फोटो पाठवा (जास्तीत जास्त {mb} MB).",
        "resume_not_resume": "🤔 ही फाईल resume वाटत नाही. कृपया तुमचा resume पाठवा.",
        "resume_failed": "😕 Resume वाचता आला नाही. पुन्हा पाठवा किंवा \"resume नाही\" निवडा.",
        "resume_summary": (
            "✅ तुमची माहिती:\n"
            "🎓 शिक्षण: {education}\n"
            "📚 कोर्स: {course}\n"
            "🛠 Skills: {skills}\n"
            "💼 अनुभव: {experience} वर्षे\n\n"
            "ही माहिती बरोबर आहे का?"
        ),
        "confirm_btn": "✅ बरोबर आहे",
        "edit_btn": "✏️ बदला",
        "ask_education": "🎓 तुमचं सर्वोच्च शिक्षण लिहा\nउदा. 12th, B.Com, Diploma Mechanical, BE Computer",
        "ask_course": "📚 तुमचा कोर्स / शाखा लिहा\nउदा. Computer Science, Accounts, ITI Fitter\nकाही नसेल तर - लिहा.",
        "ask_skills": "🛠 तुमचे skills स्वल्पविराम देऊन लिहा\nउदा. MS Excel, Tally, Typing\nकाही नसेल तर - लिहा.",
        "ask_categories": "💼 तुम्हाला कोणत्या प्रकारची नोकरी हवी आहे?\nजास्तीत जास्त {max} निवडा, मग पुढे दाबा.",
        "type_category_btn": "✍️ दुसरी टाईप करा",
        "more_categories_btn": "📂 सर्व categories",
        "next_btn": "पुढे ➡️",
        "type_category": "✍️ तुम्हाला हवी असलेली नोकरी टाईप करा\nउदा. computer operator, bank, nurse",
        "category_not_found": "😕 ही category सापडली नाही. खालील यादीतून निवडा.",
        "category_added": "✅ {name} जोडली.",
        "max_categories": "⚠️ जास्तीत जास्त {max} categories निवडता येतात.",
        "pick_one_category": "⚠️ किमान 1 category निवडा.",
        "ask_job_types": "🏢 नोकरीचा प्रकार निवडा (एक किंवा जास्त), मग पुढे दाबा:",
        "jt_govt": "🏛 सरकारी",
        "jt_private": "🏢 प्रायव्हेट",
        "jt_internship": "🎓 इंटर्नशिप",
        "jt_wfh": "🏠 Work from home",
        "profile_done_trial": (
            "🎉 प्रोफाइल पूर्ण झाली, {name}!\n"
            "🎁 तुम्हाला {days} दिवस FREE trial मिळाला आहे.\n"
            "⏰ रोज {times} वाजता तुमच्या category चे jobs येतील.\n\n"
            "/jobs - आत्ताचे jobs पाहा\n/profile - प्रोफाइल\n/subscribe - Subscription"
        ),
        "profile_done_no_trial": "✅ प्रोफाइल अपडेट झाली!",
        "digest_header": "🔔 आजचे तुमच्यासाठी {count} jobs",
        "job_line": "{n}. {title}\n🏢 {company}\n📍 {location} • {job_type}{qualification}{salary}{last_date}",
        "qualification_part": "\n🎓 {qualification}",
        "salary_part": "\n💰 {salary}",
        "last_date_part": "\n⏳ शेवटची तारीख: {date}",
        "apply_btn": "{n}. Apply",
        "no_jobs_now": "🙂 सध्या तुमच्या category मध्ये नवीन jobs नाहीत. नवीन आले की लगेच पाठवू.",
        "locked_teaser": (
            "🔒 तुमच्या category मध्ये {count} नवीन jobs आले आहेत!\n"
            "फक्त ₹{price} मध्ये {days} दिवस रोज jobs मिळवा."
        ),
        "no_access": "🔒 तुमचा trial / subscription संपला आहे.\nरोज jobs मिळवण्यासाठी subscribe करा.",
        "subscribe_info": (
            "⭐ Job Alerts Subscription\n"
            "💰 ₹{price} / {days} दिवस\n"
            "✅ रोज तुमच्या category चे jobs\n"
            "✅ Govt + Private + Internship\n\n"
            "खालील बटण दाबून UPI / Card ने पेमेंट करा.\n"
            "पेमेंट झाल्यावर subscription आपोआप चालू होईल.\n\n"
            "ही सेवा job alerts साठी आहे, नोकरीची हमी नाही."
        ),
        "pay_btn": "💳 ₹{price} पेमेंट करा",
        "payment_error": "😕 पेमेंट लिंक तयार करता आली नाही. थोड्या वेळाने पुन्हा प्रयत्न करा.",
        "payment_success": "✅ पेमेंट यशस्वी!\nतुमचं subscription {until} पर्यंत चालू आहे. 🎉",
        "status_active": "✅ Subscription चालू: {until} पर्यंत",
        "status_trial": "🎁 Free trial चालू: {until} पर्यंत",
        "status_none": "❌ Subscription नाही",
        "profile_view": (
            "👤 {name}\n📱 {phone}\n📍 {district}\n🎓 {education}\n📚 {course}\n"
            "💼 Categories: {categories}\n🏢 प्रकार: {job_types}\n\n{status}"
        ),
        "edit_profile_btn": "✏️ प्रोफाइल बदला",
        "edit_categories_btn": "💼 Category बदला",
        "reminder_expiring": "⏰ तुमचं subscription {until} ला संपणार आहे.\nJobs बंद होऊ नयेत म्हणून आत्ताच renew करा.",
        "renew_btn": "🔄 Renew ₹{price}",
        "blocked": "⛔ तुमचं खातं बंद केलं आहे. मदतीसाठी संपर्क करा.",
        "help": (
            "ℹ️ मदत\n\n/jobs - आत्ताचे jobs\n/profile - प्रोफाइल पाहा/बदला\n"
            "/category - Category बदला\n/subscribe - Subscription\n"
            "/language - भाषा बदला{support}"
        ),
        "support_line": "\n📞 Support: @{username}",
        "finish_onboarding": "👉 आधी प्रोफाइल पूर्ण करा. /start दाबा.",
        "any_location": "कुठेही",
        "not_given": "-",
        "other_district_value": "__other__",
    },
    "hi": {
        "choose_language": "🙏 नमस्ते! Job Alert Bot में आपका स्वागत है.\n\nअपनी भाषा चुनें / Choose your language:",
        "ask_name": "👤 अपना पूरा नाम लिखें\nजैसे राहुल सुरेश पाटिल",
        "bad_name": "⚠️ कृपया सही पूरा नाम लिखें (कम से कम 2 शब्द, केवल अक्षर).",
        "ask_phone": "📱 नीचे का बटन दबाकर अपना मोबाइल नंबर शेयर करें.",
        "share_phone_btn": "📱 नंबर शेयर करें",
        "phone_not_own": "⚠️ कृपया अपना नंबर शेयर करें, नीचे के बटन से.",
        "use_button": "👇 कृपया नीचे का बटन इस्तेमाल करें.",
        "ask_district": "📍 अपना जिला चुनें या लिखें:",
        "other_district_btn": "✍️ दूसरा जिला",
        "type_district": "✍️ अपने जिले का नाम लिखें:",
        "ask_resume": "📄 अपना Resume भेजें\nPDF, Word (DOCX) या resume की साफ फोटो चलेगी.",
        "no_resume_btn": "❌ मेरे पास resume नहीं है",
        "resume_checking": "⏳ Resume जांच रहे हैं... 10-20 सेकंड लगेंगे.",
        "resume_bad_file": "⚠️ यह फाइल नहीं चलेगी. PDF, DOCX या फोटो भेजें (अधिकतम {mb} MB).",
        "resume_not_resume": "🤔 यह फाइल resume नहीं लगती. कृपया अपना resume भेजें.",
        "resume_failed": "😕 Resume पढ़ नहीं पाए. दोबारा भेजें या \"resume नहीं\" चुनें.",
        "resume_summary": (
            "✅ आपकी जानकारी:\n"
            "🎓 शिक्षा: {education}\n"
            "📚 कोर्स: {course}\n"
            "🛠 Skills: {skills}\n"
            "💼 अनुभव: {experience} साल\n\n"
            "क्या यह जानकारी सही है?"
        ),
        "confirm_btn": "✅ सही है",
        "edit_btn": "✏️ बदलें",
        "ask_education": "🎓 अपनी सबसे ऊंची शिक्षा लिखें\nजैसे 12th, B.Com, Diploma Mechanical",
        "ask_course": "📚 अपना कोर्स / ब्रांच लिखें. कुछ नहीं हो तो - लिखें.",
        "ask_skills": "🛠 अपने skills कॉमा लगाकर लिखें\nजैसे MS Excel, Tally, Typing\nकुछ नहीं हो तो - लिखें.",
        "ask_categories": "💼 आपको किस तरह की नौकरी चाहिए?\nअधिकतम {max} चुनें, फिर आगे दबाएं.",
        "type_category_btn": "✍️ दूसरी लिखें",
        "more_categories_btn": "📂 सभी categories",
        "next_btn": "आगे ➡️",
        "type_category": "✍️ जो नौकरी चाहिए वह लिखें\nजैसे computer operator, bank, nurse",
        "category_not_found": "😕 यह category नहीं मिली. नीचे की सूची से चुनें.",
        "category_added": "✅ {name} जोड़ी गई.",
        "max_categories": "⚠️ अधिकतम {max} categories चुन सकते हैं.",
        "pick_one_category": "⚠️ कम से कम 1 category चुनें.",
        "ask_job_types": "🏢 नौकरी का प्रकार चुनें (एक या ज्यादा), फिर आगे दबाएं:",
        "jt_govt": "🏛 सरकारी",
        "jt_private": "🏢 प्राइवेट",
        "jt_internship": "🎓 इंटर्नशिप",
        "jt_wfh": "🏠 Work from home",
        "profile_done_trial": (
            "🎉 प्रोफाइल पूरी हो गई, {name}!\n"
            "🎁 आपको {days} दिन FREE trial मिला है.\n"
            "⏰ रोज {times} बजे आपकी category की jobs आएंगी.\n\n"
            "/jobs - अभी की jobs\n/profile - प्रोफाइल\n/subscribe - Subscription"
        ),
        "profile_done_no_trial": "✅ प्रोफाइल अपडेट हो गई!",
        "digest_header": "🔔 आज आपके लिए {count} jobs",
        "job_line": "{n}. {title}\n🏢 {company}\n📍 {location} • {job_type}{qualification}{salary}{last_date}",
        "qualification_part": "\n🎓 {qualification}",
        "salary_part": "\n💰 {salary}",
        "last_date_part": "\n⏳ आखिरी तारीख: {date}",
        "apply_btn": "{n}. Apply",
        "no_jobs_now": "🙂 अभी आपकी category में नई jobs नहीं हैं. नई आते ही भेजेंगे.",
        "locked_teaser": (
            "🔒 आपकी category में {count} नई jobs आई हैं!\n"
            "सिर्फ ₹{price} में {days} दिन रोज jobs पाएं."
        ),
        "no_access": "🔒 आपका trial / subscription खत्म हो गया है.\nरोज jobs पाने के लिए subscribe करें.",
        "subscribe_info": (
            "⭐ Job Alerts Subscription\n"
            "💰 ₹{price} / {days} दिन\n"
            "✅ रोज आपकी category की jobs\n"
            "✅ Govt + Private + Internship\n\n"
            "नीचे का बटन दबाकर UPI / Card से पेमेंट करें.\n"
            "पेमेंट होते ही subscription अपने आप चालू होगा.\n\n"
            "यह सेवा job alerts के लिए है, नौकरी की गारंटी नहीं."
        ),
        "pay_btn": "💳 ₹{price} पेमेंट करें",
        "payment_error": "😕 पेमेंट लिंक नहीं बन पाई. थोड़ी देर बाद कोशिश करें.",
        "payment_success": "✅ पेमेंट सफल!\nआपका subscription {until} तक चालू है. 🎉",
        "status_active": "✅ Subscription चालू: {until} तक",
        "status_trial": "🎁 Free trial चालू: {until} तक",
        "status_none": "❌ Subscription नहीं है",
        "profile_view": (
            "👤 {name}\n📱 {phone}\n📍 {district}\n🎓 {education}\n📚 {course}\n"
            "💼 Categories: {categories}\n🏢 प्रकार: {job_types}\n\n{status}"
        ),
        "edit_profile_btn": "✏️ प्रोफाइल बदलें",
        "edit_categories_btn": "💼 Category बदलें",
        "reminder_expiring": "⏰ आपका subscription {until} को खत्म होगा.\nJobs बंद न हों, इसलिए अभी renew करें.",
        "renew_btn": "🔄 Renew ₹{price}",
        "blocked": "⛔ आपका खाता बंद कर दिया गया है. मदद के लिए संपर्क करें.",
        "help": (
            "ℹ️ मदद\n\n/jobs - अभी की jobs\n/profile - प्रोफाइल\n"
            "/category - Category बदलें\n/subscribe - Subscription\n"
            "/language - भाषा बदलें{support}"
        ),
        "support_line": "\n📞 Support: @{username}",
        "finish_onboarding": "👉 पहले प्रोफाइल पूरी करें. /start दबाएं.",
        "any_location": "कहीं भी",
        "not_given": "-",
        "other_district_value": "__other__",
    },
    "en": {
        "choose_language": "🙏 Hello! Welcome to Job Alert Bot.\n\nChoose your language:",
        "ask_name": "👤 Type your full name\ne.g. Rahul Suresh Patil",
        "bad_name": "⚠️ Please enter a valid full name (at least 2 words, letters only).",
        "ask_phone": "📱 Tap the button below to share your mobile number.",
        "share_phone_btn": "📱 Share number",
        "phone_not_own": "⚠️ Please share your own number using the button below.",
        "use_button": "👇 Please use the button below.",
        "ask_district": "📍 Select or type your district:",
        "other_district_btn": "✍️ Other district",
        "type_district": "✍️ Type your district name:",
        "ask_resume": "📄 Send your Resume\nPDF, Word (DOCX) or a clear photo of your resume.",
        "no_resume_btn": "❌ I don't have a resume",
        "resume_checking": "⏳ Checking your resume... takes 10-20 seconds.",
        "resume_bad_file": "⚠️ This file is not supported. Send PDF, DOCX or a photo (max {mb} MB).",
        "resume_not_resume": "🤔 This doesn't look like a resume. Please send your resume.",
        "resume_failed": "😕 Couldn't read the resume. Send it again or choose \"no resume\".",
        "resume_summary": (
            "✅ Your details:\n"
            "🎓 Education: {education}\n"
            "📚 Course: {course}\n"
            "🛠 Skills: {skills}\n"
            "💼 Experience: {experience} years\n\n"
            "Is this correct?"
        ),
        "confirm_btn": "✅ Correct",
        "edit_btn": "✏️ Edit",
        "ask_education": "🎓 Type your highest education\ne.g. 12th, B.Com, Diploma Mechanical",
        "ask_course": "📚 Type your course / branch. Type - if none.",
        "ask_skills": "🛠 Type your skills separated by commas\ne.g. MS Excel, Tally, Typing\nType - if none.",
        "ask_categories": "💼 What kind of job do you want?\nSelect up to {max}, then tap Next.",
        "type_category_btn": "✍️ Type another",
        "more_categories_btn": "📂 All categories",
        "next_btn": "Next ➡️",
        "type_category": "✍️ Type the job you want\ne.g. computer operator, bank, nurse",
        "category_not_found": "😕 Couldn't find that category. Pick from the list below.",
        "category_added": "✅ Added {name}.",
        "max_categories": "⚠️ You can select up to {max} categories.",
        "pick_one_category": "⚠️ Select at least 1 category.",
        "ask_job_types": "🏢 Select job type (one or more), then tap Next:",
        "jt_govt": "🏛 Government",
        "jt_private": "🏢 Private",
        "jt_internship": "🎓 Internship",
        "jt_wfh": "🏠 Work from home",
        "profile_done_trial": (
            "🎉 Profile complete, {name}!\n"
            "🎁 You got a {days}-day FREE trial.\n"
            "⏰ Jobs for your categories arrive daily at {times}.\n\n"
            "/jobs - jobs right now\n/profile - your profile\n/subscribe - subscription"
        ),
        "profile_done_no_trial": "✅ Profile updated!",
        "digest_header": "🔔 {count} jobs for you today",
        "job_line": "{n}. {title}\n🏢 {company}\n📍 {location} • {job_type}{qualification}{salary}{last_date}",
        "qualification_part": "\n🎓 {qualification}",
        "salary_part": "\n💰 {salary}",
        "last_date_part": "\n⏳ Last date: {date}",
        "apply_btn": "{n}. Apply",
        "no_jobs_now": "🙂 No new jobs in your categories right now. We'll send them as soon as they arrive.",
        "locked_teaser": (
            "🔒 {count} new jobs arrived in your categories!\n"
            "Get daily jobs for {days} days at just ₹{price}."
        ),
        "no_access": "🔒 Your trial / subscription has ended.\nSubscribe to keep getting daily jobs.",
        "subscribe_info": (
            "⭐ Job Alerts Subscription\n"
            "💰 ₹{price} / {days} days\n"
            "✅ Daily jobs for your categories\n"
            "✅ Govt + Private + Internship\n\n"
            "Tap below to pay by UPI / Card.\n"
            "Your subscription activates automatically after payment.\n\n"
            "This is a job-alert service, not a job guarantee."
        ),
        "pay_btn": "💳 Pay ₹{price}",
        "payment_error": "😕 Couldn't create the payment link. Please try again shortly.",
        "payment_success": "✅ Payment successful!\nYour subscription is active until {until}. 🎉",
        "status_active": "✅ Subscription active until {until}",
        "status_trial": "🎁 Free trial until {until}",
        "status_none": "❌ No subscription",
        "profile_view": (
            "👤 {name}\n📱 {phone}\n📍 {district}\n🎓 {education}\n📚 {course}\n"
            "💼 Categories: {categories}\n🏢 Types: {job_types}\n\n{status}"
        ),
        "edit_profile_btn": "✏️ Edit profile",
        "edit_categories_btn": "💼 Change categories",
        "reminder_expiring": "⏰ Your subscription ends on {until}.\nRenew now so your jobs don't stop.",
        "renew_btn": "🔄 Renew ₹{price}",
        "blocked": "⛔ Your account has been blocked. Please contact support.",
        "help": (
            "ℹ️ Help\n\n/jobs - jobs now\n/profile - view/edit profile\n"
            "/category - change categories\n/subscribe - subscription\n"
            "/language - change language{support}"
        ),
        "support_line": "\n📞 Support: @{username}",
        "finish_onboarding": "👉 Please complete your profile first. Tap /start.",
        "any_location": "Anywhere",
        "not_given": "-",
        "other_district_value": "__other__",
    },
}


def t(lang: str | None, key: str, **kwargs) -> str:
    """Look up a text key for a language, falling back mr -> en -> the raw key."""
    for candidate_lang in (lang, "mr", "en"):
        if candidate_lang and candidate_lang in TEXTS and key in TEXTS[candidate_lang]:
            template = TEXTS[candidate_lang][key]
            try:
                return template.format(**kwargs)
            except (KeyError, IndexError):
                return template
    return key
