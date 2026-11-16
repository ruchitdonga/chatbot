# Error Samples

Random intent or slot errors (test split), up to 3 per locale and run, seed from the config. For the manual error analysis (at least 20 cases).

## bert-base-multilingual-cased-runA

| Locale | Utterance | Gold intent | Predicted | Confidence | Gold slots | Predicted slots |
|---|---|---|---|---|---|---|
| en-US | what's happening around town | recommendation_events | recommendation_events | 0.9969 | place_name: around town | place_name: town |
| en-US | play my spotify dance play list | play_music | play_music | 0.9731 | - | app_name: spotify, playlist_name: dance play |
| en-US | play the weekend | play_music | play_audiobook | 0.521 | song_name: weekend | date: weekend |
| es-ES | bautizo de la hija de cristina | calendar_set | qa_factoid | 0.7931 | event_name: bautizo de la hija, person: de cristina | relation: hija, person: cristina |
| es-ES | hay servicio de aparcacoches en el evento | calendar_query | calendar_query | 0.9415 | relation: aparcacoches | event_name: aparcacoches |
| es-ES | bloquea una hora desde las diez de mañana por la mañana | calendar_set | alarm_set | 0.9148 | time: una hora, time: diez, date: mañana, timeofday: por la mañana | time: diez de mañana, timeofday: mañana |
| de-DE | errechne den zeitunterschied zwischen acht uhr dreißig g. t. m. und fünf uhr dreißig g. m. t. | datetime_convert | datetime_convert | 0.9698 | time: acht uhr dreißig, time_zone: g. t. m. | time: acht uhr dreiß, time: fünf uhr |
| de-DE | ändere die lautstärke auf fünfunddreißig prozent | audio_volume_other | audio_volume_up | 0.4792 | change_amount: auf fünfunddreißig prozent | change_amount: auf fünfunddreißig prozent |
| de-DE | was ist mit dir | general_quirky | general_greet | 0.5135 | - | - |
| fr-FR | dis-moi tout sur l'ouragan | qa_definition | general_quirky | 0.7526 | definition_word: l'ouragan | news_topic: ouragan |
| fr-FR | s'il vous plait élevez la lumière je ne suis pas confortable à ça | iot_hue_lightup | iot_hue_lightdim | 0.9166 | - | - |
| fr-FR | quelle est la blague la plus drôle que tu connais | general_joke | general_joke | 0.9979 | joke_type: drôle | joke_type: plus, joke_type: drôle |
| ja-JP | ライトを中くらいまで落とす | iot_hue_lightoff | iot_hue_lightdim | 0.9947 | - | time: 中くらい |
| ja-JP | 今日のイベントの予定を教えて | calendar_query | calendar_query | 0.9977 | date: 今日の | date: 今日 |
| ja-JP | カレンダーを消去してよお願い | calendar_remove | calendar_remove | 0.9993 | time: 消去 | - |
| hi-IN | नेटवर्क से संबंधित मुद्दों के लिए एयरसेल को शिकायत अग्रेषित करें | social_post | social_post | 0.9081 | business_name: एयरसेल | - |
| hi-IN | सप्ताह के मौसम के विवरण को संक्षेप में प्रस्तुत करें | weather_query | weather_query | 0.8385 | time: सप्ताह | date: सप्ताह |
| hi-IN | मेरे पास राम के लिए कितने फ़ोन नंबर हैं | email_querycontact | email_querycontact | 0.5521 | person: राम, personal_info: फ़ोन नंबर | person: राम |
| ar-SA | شغلي موسيقى حق ماجد المهندس | play_music | qa_factoid | 0.7253 | artist_name: ماجد المهندس | person: ماجد المهندس |
| ar-SA | روح لجهات الإتصال و أختار عنوان email جديد | email_sendemail | email_sendemail | 0.9475 | - | person: روح |
| ar-SA | أبي أعرف المقاهي اللي عندها أفضل تقييمات في المنطقة | recommendation_locations | recommendation_locations | 0.6249 | business_type: المقاهي | - |
| sw-KE | je utawasha muziki | play_music | music_likeness | 0.6208 | - | artist_name: utawasha muziki |
| sw-KE | mipango ya sherehe yangu | calendar_query | music_likeness | 0.2776 | event_name: sherehe | - |
| sw-KE | mchumba wa sanaipei tande wa hivi karibuni ana umri gani | qa_factoid | qa_factoid | 0.8007 | person: sanaipei tande | - |
| am-ET | ተራ ጥያቄዎችን ጠይቅ | general_quirky | play_radio | 0.23 | - | - |
| am-ET | እኔ ይሄን ዘፈን እወደዋለሁ | music_likeness | play_radio | 0.2778 | - | - |
| am-ET | መብራቶችን ወደታች መልስ | iot_hue_lightdim | play_radio | 0.2293 | - | - |
| ta-IN | அடுத்த தற்போதைய போட்காஸ்ட் போடு | play_podcasts | news_query | 0.7515 | podcast_name: தற்போதைய | news_topic: ோ |
| ta-IN | சிறந்த கிண்ணம் அதிகாரப்பூர்வமாக எப்போது தொடங்கும் | qa_factoid | general_quirky | 0.9949 | event_name: சிறந்த கிண்ணம் | - |
| ta-IN | அடுத்த நிகழ்வை நீக்க முடியுமா | calendar_remove | calendar_set | 0.8094 | - | - |

## bert-base-multilingual-cased-runB

| Locale | Utterance | Gold intent | Predicted | Confidence | Gold slots | Predicted slots |
|---|---|---|---|---|---|---|
| en-US | show me reviews of my nearest location food court | recommendation_locations | recommendation_locations | 0.7201 | place_name: nearest location, business_type: food court | business_type: food court |
| en-US | what song is on the radio | music_query | play_radio | 0.88 | - | - |
| en-US | play a retro song in my playlist | play_music | play_music | 0.9881 | music_genre: retro | music_genre: ret, music_descriptor: ro song |
| es-ES | es el cumpleaños de alguien | calendar_query | qa_factoid | 0.8975 | event_name: cumpleaños | event_name: cumpleaños |
| es-ES | tengo una reunión hoy al mediodía | calendar_set | calendar_query | 0.9977 | event_name: reunión, date: hoy, timeofday: mediodía | event_name: reunión, date: hoy, timeofday: mediodía |
| es-ES | poner un aviso para tres dos y una horas antes del examen final de inglés de la próxima semana | calendar_set | calendar_set | 0.9351 | event_name: examen final de inglés, date: de la próxima semana | time: tres dos y una horas, event_name: examen final de inglés, date: próxima semana |
| de-DE | stelle einen wecker für neun uhr nächsten sonntag | alarm_set | alarm_set | 0.9979 | time: neun uhr, date: nächsten sonntag | time: neun uhr, date: sonntag |
| de-DE | kannst du bitte imogen heap spielen | play_music | play_music | 0.3889 | artist_name: imogen heap | song_name: im, audiobook_name: ogen heap |
| de-DE | ändere die zeitzone zu deutschland | datetime_convert | datetime_convert | 0.9902 | place_name: deutschland | place_name: deutsch, time_zone: land |
| fr-FR | quel est l'heure du tgv | transport_query | datetime_query | 0.9177 | transport_name: tgv | media_type: t, time_zone: gv |
| fr-FR | vite | audio_volume_up | general_greet | 0.3741 | - | - |
| fr-FR | si c'est le lever du soleil à ottawa quelle heure est-il à paris | datetime_convert | weather_query | 0.459 | time: lever du soleil, place_name: ottawa, place_name: paris | place_name: ottawa, place_name: paris |
| ja-JP | 二十二日は水曜日ですか | datetime_query | datetime_query | 0.986 | date: 二十二日 | date: 二十二日, date: 水曜日 |
| ja-JP | 奇数日の日曜にはリマインダーを設定する | calendar_set | calendar_set | 0.998 | general_frequency: 奇数日の日曜 | date: 奇数日の, date: 日曜 |
| ja-JP | 今日の予定を教えて | calendar_query | calendar_query | 0.9932 | - | date: 今日 |
| hi-IN | मुझे अर्थव्यवस्था के बारे में बताओ और जी. डी. पी. भारत बनाम चीन के बारे में | general_quirky | general_quirky | 0.8794 | place_name: भारत, place_name: चीन | place_name: भारत, place_name: चीन |
| hi-IN | कुछ भक्ति संगीत चालू करें | play_music | play_music | 0.9571 | music_descriptor: भक्ति | music_genre: भक्ति |
| hi-IN | रानी का ईमेल दिखाओ और उसे लिखो कि मैं उसे बता दूंगा | email_sendemail | email_sendemail | 0.9981 | person: रानी का | person: रानी |
| ar-SA | أبغى أعرف اذا عندي أي تنبيهات مضبوطة حاليا | alarm_query | calendar_query | 0.8269 | - | - |
| ar-SA | ما هي الظروف المناخية في تلك المنطقة | qa_factoid | weather_query | 0.9135 | - | place_name: المنطقة |
| ar-SA | الزر التالي | play_podcasts | cooking_recipe | 0.6837 | - | - |
| sw-KE | afya | general_quirky | qa_factoid | 0.29 | - | place_name: afya |
| sw-KE | nairobi | transport_query | qa_factoid | 0.7067 | place_name: nairobi | place_name: nairobi |
| sw-KE | ninahitaji kuongezwa anwani mpya ya barua pepe kwa wawasiliani wangu | email_sendemail | email_addcontact | 0.9955 | - | - |
| am-ET | ረቡዕ ላይ የንግድ ስብሰባ ን ሰርዝ | calendar_remove | qa_factoid | 0.0664 | date: ረቡዕ, event_name: የንግድ ስብሰባ | - |
| am-ET | እኔ ይሄን ዘፈን እወደዋለሁ | music_likeness | play_music | 0.0712 | - | - |
| am-ET | የሙቀት መጠን ምንድን ነዉ | weather_query | play_music | 0.0712 | weather_descriptor: የሙቀት መጠን | - |
| ta-IN | ஆக்ராவைச் சுற்றி மின்னலே ஏதாவது நடக்கிறதா | recommendation_events | recommendation_events | 0.8752 | place_name: ஆக்ராவைச், movie_type: மின்னலே | place_name: ஆக்ராவைச் |
| ta-IN | ரோமின் திறந்த ஒலிப்புத்தக வரலாறு | play_audiobook | play_audiobook | 0.9956 | audiobook_name: ரோமின் திறந்த | audiobook_name: ரோமின், media_type: ஒலிப்புத்தக |
| ta-IN | இருபதாம் தேதி திங்கட்கிழமை எங்கள் வார இறுதிப் பயணத்தைப் பற்றி ஜானுடன் உரையாட வேண்டும் | calendar_set | calendar_set | 0.9873 | date: இருபதாம் தேதி திங்கட்கிழமை, event_name: வார இறுதிப் பயணத்தைப், person: ஜானுடன், event_name: உரையாட வேண்டும் | date: இருபதாம் தேதி திங்கட்கிழமை, date: ார இ, event_name: றுதிப் பயணத்தைப், person: ஜானுடன் |

## xlm-roberta-base-runA

| Locale | Utterance | Gold intent | Predicted | Confidence | Gold slots | Predicted slots |
|---|---|---|---|---|---|---|
| en-US | check time of ten thousand eight hundred and eighty seven train from luni station on tuesday | transport_query | transport_query | 0.9579 | transport_name: ten thousand eight hundred and eighty seven, transport_type: train, place_name: luni station, date: tuesday | transport_name: thousand eight hundred and eighty seven, transport_type: train, place_name: luni station, date: tuesday |
| en-US | does louie's do take out | takeaway_query | takeaway_query | 0.9989 | business_name: louie's | business_name: louie's, order_type: take out |
| en-US | summarize week's weather details | weather_query | weather_query | 0.9988 | time: week's | date: week's |
| es-ES | recordatorio boda raúl | calendar_query | calendar_set | 0.9995 | event_name: boda, person: raúl | event_name: boda, person: raúl |
| es-ES | programar un evento de reunión en mi calendario | calendar_set | calendar_set | 0.9995 | event_name: programar | event_name: reunión |
| es-ES | quiero una reunión hasta las tres en punto | calendar_set | calendar_set | 0.9368 | event_name: reunión, time: tres en punto | event_name: reunión, time: hasta las tres |
| de-DE | wie spät ist es in mitteleuropäischer zeitzone | datetime_query | datetime_query | 0.9985 | time_zone: mitteleuropäischer | time_zone: mitteleuropäischer, time_zone: zone |
| de-DE | rufe ein taxi berlin um mich zu erreichen schwuz kreuzberg | transport_taxi | transport_taxi | 0.9947 | transport_type: taxi berlin, place_name: schwuz kreuzberg | transport_type: taxi, place_name: berlin, place_name: schwuz kreuzberg |
| de-DE | wie ist das aktuelle wetter an meinem ort | weather_query | weather_query | 0.9971 | place_name: meinem ort | - |
| fr-FR | s'il vous plaît jouer dans mes rêves lorie pester | play_music | play_music | 0.9839 | song_name: dans mes rêves | song_name: dans mes rêves, artist_name: lorie pester |
| fr-FR | pouvez-vous vraiment voir la russie de le bordeaux | qa_factoid | qa_factoid | 0.3504 | place_name: russie, place_name: bordeaux | place_name: russie, place_name: bordeaux |
| fr-FR | parle moi de trump | news_query | news_query | 0.9783 | news_topic: trump | person: trump |
| ja-JP | ニューヨークタイムズの第一面には何が掲載されているの | news_query | news_query | 0.9994 | media_type: ニューヨークタイムズの | media_type: ニューヨークタイムズ |
| ja-JP | 今週末のフライトのために設定したアラームの起床時間は何時 | alarm_query | alarm_query | 0.9971 | date: 今週末, alarm_type: 起床 | date: 今週末 |
| ja-JP | 午後八時に今晩ドライクリーニング屋に行くとリマインドして | calendar_set | calendar_set | 0.9378 | time: 午後八時, event_name: ドライクリーニング屋に行く | time: 午後八時に, timeofday: 今晩, event_name: ドライクリーニング屋 |
| hi-IN | प्राकृतिक समाचार अधिसूचना सेट करें | news_query | news_query | 0.9894 | news_topic: प्राकृतिक | media_type: प्राकृतिक |
| hi-IN | इस डिवाइस में जो भी सूची हैं उनकी सूची बनाओ | lists_query | lists_createoradd | 0.5449 | - | - |
| hi-IN | मुझे आगे बढ़ने के लिए याद दिलाएं ताकि कोई वजन न बढ़े | calendar_set | general_quirky | 0.9255 | - | - |
| ar-SA | ممكن تقولي لي نكتة | general_joke | general_quirky | 0.9605 | - | - |
| ar-SA | وقف | play_audiobook | audio_volume_mute | 0.9922 | player_setting: وقف | - |
| ar-SA | شغل لمبات البلكونة حقي لو سمحت | iot_hue_lighton | iot_coffee | 0.297 | house_place: البلكونة | - |
| sw-KE | nipatie barua pepe mpya | email_query | email_query | 0.9909 | - | email_folder: pepe |
| sw-KE | niwekee nafasi ya tiketi ya garimoshi kwenda nairobi tafadhali | transport_ticket | transport_ticket | 0.9229 | transport_type: garimoshi, place_name: nairobi | place_name: nairobi |
| sw-KE | unajua nini kuhusu pindo katika nairobi mwaka ujao | general_quirky | general_quirky | 0.8693 | event_name: pindo, place_name: nairobi, date: mwaka ujao | person: pindo, place_name: nairobi, date: ujao |
| am-ET | የቴሌቪዥን መስመር ዝርዝርን አሳየኝ | qa_definition | music_query | 0.4742 | definition_word: የቴሌቪዥን መስመር | - |
| am-ET | የኔ የቀን መቁጠሪያ ሁሉንም ክስተቶች አጽዳ | calendar_remove | general_quirky | 0.9758 | - | - |
| am-ET | ሐሙስ በሰባት ኤ. ኤም. መቀስቀሻ ያዘጋጁ | alarm_set | calendar_set | 0.9991 | date: ሐሙስ, time: በሰባት ኤ. ኤም. | date: ሐሙስ, time: በሰባት, event_name: ኤ. ኤም., event_name: መቀስቀሻ |
| ta-IN | இன்று எனது பகுதியில் ஏதேனும் பிரீ நிகழ்ச்சிகள் நடைபெறுகிறதா | recommendation_events | recommendation_events | 0.9417 | date: இன்று எனது பகுதியில் ஏதேனும் பிரீ நிகழ்ச்சிகள் நடைபெறுகிறதா | date: இன்று, event_name: பிரீ நிகழ்ச்சி |
| ta-IN | தென் கொரியாவில் இருந்து ஜப்பானுக்கு பயணம் செய்ய எவ்வளவு நேரம் ஆகும் | qa_factoid | transport_query | 0.8944 | place_name: தென் கொரியாவில், place_name: ஜப்பானுக்கு | place_name: தென் கொரியாவில், place_name: ஜப்பானுக்கு |
| ta-IN | கிடைக்கும் மீனாட்சி உணவகம் களை வெளியே எடுக்கவும் | takeaway_query | lists_remove | 0.8067 | business_name: மீனாட்சி உணவகம் | business_name: மீனாட்சி உணவகம் |

## xlm-roberta-base-runB

| Locale | Utterance | Gold intent | Predicted | Confidence | Gold slots | Predicted slots |
|---|---|---|---|---|---|---|
| en-US | what time does the train to place leave | transport_query | transport_query | 0.9922 | transport_type: train | transport_type: train, place_name: place |
| en-US | what is eastern standard time right noe | datetime_query | datetime_query | 0.9783 | time_zone: eastern | time_zone: eastern standard |
| en-US | please ring the wake up alarm at eight am next saturday | alarm_set | alarm_set | 0.9971 | alarm_type: wake up, time: eight am, date: saturday | alarm_type: up, time: eight am, date: saturday |
| es-ES | quitar la cena de esta noche con laura | calendar_remove | calendar_remove | 0.9878 | event_name: la cena de esta noche con laura | meal_type: cena, timeofday: esta noche, person: laura |
| es-ES | por favor recuérdame que vaya a la oficina de correos | calendar_set | calendar_set | 0.9991 | - | event_name: la, event_name: oficina de correos |
| es-ES | recuérdame cuando esté en la biblioteca para sacarme una tarjeta de la biblioteca nueva | calendar_set | calendar_set | 0.9994 | place_name: biblioteca, event_name: sacarme una tarjeta de la biblioteca nueva | place_name: biblioteca, event_name: sacarme una tarjeta de la biblioteca nueva |
| de-DE | stopp starte den saft | iot_wemo_on | audio_volume_mute | 0.3326 | - | device_type: ft |
| de-DE | fahr zeit bis nach leipzig | transport_query | play_podcasts | 0.5296 | place_name: leipzig | place_name: leipzig |
| de-DE | wie ist das aktuelle wetter an meinem ort | weather_query | weather_query | 0.9988 | place_name: meinem ort | - |
| fr-FR | mets seulement ma liste | play_music | lists_query | 0.9656 | - | - |
| fr-FR | liste des informations de taux de change pour la journée pour dollar à euro | qa_currency | qa_currency | 0.9986 | currency_name: dollar, currency_name: euro | time: journée, currency_name: dollar, currency_name: euro |
| fr-FR | s'il vous plait élevez la lumière je ne suis pas confortable à ça | iot_hue_lightup | iot_hue_lightoff | 0.9623 | - | - |
| ja-JP | トランプ大統領の新外交政策について教えて | news_query | news_query | 0.9988 | news_topic: トランプ大統領の新外交政策 | person: トランプ, news_topic: 大統領の新外交政策 |
| ja-JP | 明かりを消して | iot_hue_lightdim | iot_hue_lightoff | 0.9617 | - | - |
| ja-JP | 他のすべての会議をキャンセルして忠の誕生日として三月二日を私のカレンダーのイベントとしてタグ付けする | calendar_set | calendar_remove | 0.7293 | person: 忠の, event_name: 誕生日, date: 三月二日 | event_name: 会議, person: 忠の, event_name: 誕生日, date: 三月二日 |
| hi-IN | मुझे कल एक घंटे पहले बैठक के बारे में याद दिलाएं | calendar_set | calendar_set | 0.9995 | date: कल, event_name: बैठक | date: कल, time: एक घंटे, event_name: बैठक |
| hi-IN | कॉन्टेक्ट्स खोलो | email_addcontact | lists_remove | 0.6101 | - | - |
| hi-IN | कृपया folder app खोलें | takeaway_order | lists_remove | 0.3596 | - | - |
| ar-SA | أظهر لي آخر الايميلات من الراجحي | email_query | email_query | 0.9996 | business_name: الراجحي | person: الراجحي |
| ar-SA | نباتي | general_quirky | cooking_recipe | 0.8913 | - | food_type: نباتي |
| ar-SA | أرسل email لأخويا وقول ذكرى عيد زواج | email_sendemail | email_sendemail | 0.9994 | relation: لأخويا, event_name: ذكرى عيد زواج | relation: لأخويا, event_name: عيد زواج |
| sw-KE | ni sinema gani kwenye kumbi za sinema ambayo haiudhi | recommendation_movies | recommendation_movies | 0.9548 | place_name: kumbi za sinema | business_type: mbi, business_type: sinema |
| sw-KE | matangazo ya maeneo | general_quirky | play_radio | 0.7406 | - | - |
| sw-KE | endesha gari na uwalete marafiki zangu | general_quirky | general_quirky | 0.9159 | - | transport_type: gari, relation: mara |
| am-ET | ሁል ቀን ከሰአት መድሃኒት እንድወስድ አስታዋሽ አበጅ | calendar_set | calendar_set | 0.9984 | general_frequency: ሁል ቀን, timeofday: ከሰአት | general_frequency: ሁል ቀን, timeofday: ከሰአት, event_name: መድሃኒት, event_name: ወስድ |
| am-ET | ማድረስ መስራት ይችላሉ | takeaway_query | play_music | 0.529 | order_type: ማድረስ | order_type: ድ |
| am-ET | አሁን እና ወደፊት በአየር ማጽጃ ማሽን ንጹህ ይልበሱ እና ሳሎን ያፅዱ | iot_cleaning | iot_cleaning | 0.9959 | device_type: በአየር ማጽጃ ማሽን, house_place: ሳሎን | device_type: በአየር ማጽጃ ማሽን, house_place: ሳ |
| ta-IN | சென்னை தொடர் வண்டி பயணச்சீட்டு எங்கே | transport_ticket | transport_query | 0.9935 | place_name: சென்னை, transport_type: தொடர் வண்டி | place_name: சென்னை, transport_type: தொடர் வண்டி |
| ta-IN | சேவல் சண்டாயை கொண்டு வாருங்கள் | play_game | play_game | 0.6364 | game_name: சேவல் சண்டாயை | game_name: சே, game_name: ண்டா |
| ta-IN | ஹயாத்தி மகள் வளைகாப்பு | calendar_set | general_quirky | 0.5511 | person: ஹயாத்தி, event_name: மகள் வளைகாப்பு | person: ஹயாத்தி மகள் |

## xlm-roberta-base-runB-oos

| Locale | Utterance | Gold intent | Predicted | Confidence | Gold slots | Predicted slots |
|---|---|---|---|---|---|---|
| en-US | book a train ticket weekend of the twenty sixth phoenix to los angeles | transport_ticket | transport_ticket | 0.9981 | transport_type: train, date: weekend of the twenty sixth, place_name: phoenix, place_name: los angeles | transport_type: train, date: weekend of the twenty sixth phoenix, place_name: los angeles |
| en-US | how many tornadoes have there been this month | general_quirky | general_quirky | 0.6614 | news_topic: tornadoes, date: this month | news_topic: does, date: this month |
| en-US | play bilando | play_music | play_music | 0.5419 | song_name: bilando | game_name: bilando |
| es-ES | crea un recordatorio recurrente para este evento de calendario | calendar_set | calendar_set | 0.9996 | - | general_frequency: current |
| es-ES | agregue la fecha de la cena de mañana al calendario | calendar_set | calendar_set | 0.9993 | meal_type: cena, date: de mañana | meal_type: cena, date: mañana |
| es-ES | hey cancela mis otras reuniones y llamadas para el dos de marzo porque es el cumpleaños de fernando y etiquétalo como un evento en tu calendario | calendar_set | calendar_remove | 0.9932 | date: dos de marzo, event_name: cumpleaños, person: de fernando | event_name: reuniones, event_name: llamadas, date: dos de marzo, event_name: cumpleaños, person: de fernando |
| de-DE | kann man bei kreuzburger zum mitnehmen bestellen | takeaway_query | takeaway_order | 0.7642 | business_name: kreuzburger | business_name: kreuzburger, order_type: zum mitnehmen |
| de-DE | wie kaufe ich online ein zug ticket | transport_query | transport_ticket | 0.8745 | transport_type: zug | transport_type: zug |
| de-DE | ist das abendessen schon fertig | takeaway_query | calendar_query | 0.927 | meal_type: abendessen | meal_type: abendessen |
| fr-FR | baisse les lumières à moyen | iot_hue_lightoff | iot_hue_lightdim | 0.9967 | - | change_amount: à moyen |
| fr-FR | quel est le plus grand pupitre | qa_definition | qa_factoid | 0.9991 | definition_word: le plus grand pupitre | - |
| fr-FR | est ce qu'il fera beau demain | weather_query | weather_query | 0.9926 | - | weather_descriptor: beau, date: demain |
| ja-JP | pandora | play_music | play_radio | 0.9766 | - | app_name: pandora |
| ja-JP | 九十年代のラップでヒットした曲を再生して | play_music | play_music | 0.9956 | music_genre: 九十年代のラップ | music_genre: 九十, music_genre: ラップ |
| ja-JP | 木曜日午前十一時にママを美容院に連れて行くことをリマインドして | calendar_set | calendar_set | 0.9982 | date: 木曜日, time: 午前十一時, relation: ママ, relation: 美容院 | date: 木曜日, time: 午前十一時に, relation: ママ, event_name: 美容院 |
| hi-IN | पंजीकरण खुलने पर मुझे सचेत करें | calendar_set | calendar_set | 0.9615 | event_name: पंजीकरण | - |
| hi-IN | लखनऊ उत्तर प्रदेश में स्थित मेरे संपर्क ईमेल में श्याम हार्डवेयर जोड़े | email_addcontact | email_addcontact | 0.9546 | place_name: लखनऊ उत्तर प्रदेश | place_name: लखनऊ उत्तर प्रदेश, person: श्याम, personal_info: हार्डवेयर |
| hi-IN | मुझे अच्छे से रोने की ज़रूरत है क्या आप मेरे लिए उदास शास्त्रीय गाने बजा सकते हैं | play_music | play_music | 0.9912 | music_descriptor: उदास, music_genre: शास्त्रीय | music_genre: उदास शास्त्रीय |
| ar-SA | الجو خايس اليوم | general_quirky | weather_query | 0.9981 | date: اليوم | weather_descriptor: خايس, date: اليوم |
| ar-SA | شوف رقم ماما | email_querycontact | email_querycontact | 0.9983 | relation: ماما | personal_info: رقم, relation: ماما |
| ar-SA | استدعاء تاكسي المدينة إلى المطار | transport_taxi | transport_taxi | 0.9983 | transport_type: تاكسي, place_name: المطار | transport_type: تاكسي, place_name: المدينة, place_name: المطار |
| sw-KE | unajua nini kuhusu pindo katika nairobi mwaka ujao | general_quirky | calendar_query | 0.7541 | event_name: pindo, place_name: nairobi, date: mwaka ujao | event_name: pindo, place_name: nairobi, date: mwaka ujao |
| sw-KE | unajua namba ya simu ya margaret kenyatta | qa_factoid | email_querycontact | 0.9947 | person: margaret kenyatta | personal_info: namba ya simu, person: margaret kenyatta |
| sw-KE | usiniache nisahau kumnunulia zawadi dada yangu | calendar_set | social_post | 0.4137 | relation: dada | relation: dada |
| am-ET | ኦሊ ቤት ማምጣት ይችላሉ | takeaway_query | takeaway_query | 0.5385 | order_type: ማምጣት | order_type: ማም |
| am-ET | ይሄ ዘፈን በ ጂጂ ነው | music_query | music_query | 0.9969 | artist_name: ጂጂ | music_genre: ጂጂ |
| am-ET | አስተላላፊ አጋፋሪ | recommendation_events | social_post | 0.8714 | event_name: አጋፋሪ | - |
| ta-IN | இரண்டாவது வீரராக கான்ட்ரா விளையாட்டை விளையாடுங்கள் | play_game | play_game | 0.8298 | game_name: கான்ட்ரா | - |
| ta-IN | சந்திப்புகளைக் காட்டு | calendar_set | calendar_query | 0.986 | event_name: சந்திப்புகளைக் | event_name: சந்திப்புகளைக் |
| ta-IN | குளிர்காலத்தில் காலையில் எனக்கு சூடான சாக்ஸ் தேவைப்படுமா | weather_query | weather_query | 0.9995 | weather_descriptor: குளிர்காலத்தில், timeofday: காலையில், weather_descriptor: சூடான சாக்ஸ் | date: குளிர், time: காலத்தில், timeofday: காலையில், weather_descriptor: சூடான சாக்ஸ் |

## xlm-roberta-base-runB-oos-int8

| Locale | Utterance | Gold intent | Predicted | Confidence | Gold slots | Predicted slots |
|---|---|---|---|---|---|---|
| en-US | cisco system | recommendation_movies | qa_stock | 0.5827 | - | - |
| en-US | will the temperature stay about the same or is it going to get colder | weather_query | weather_query | 0.9963 | weather_descriptor: temperature | weather_descriptor: temperature, weather_descriptor: colder |
| en-US | please ring the wake up alarm at eight am next saturday | alarm_set | alarm_set | 0.9966 | alarm_type: wake up, time: eight am, date: saturday | alarm_type: up, time: eight am, date: saturday |
| es-ES | ok google borra cumpleaños de javier del calendario | calendar_remove | calendar_remove | 0.998 | event_name: cumpleaños de javier | event_name: cumpleaños, person: de javier |
| es-ES | yo tengo una cita el viernes | calendar_query | calendar_query | 0.983 | date: viernes | event_name: cita, date: viernes |
| es-ES | lo que está en la agenda de las cuatro de la tarde reunión con benito | calendar_query | calendar_query | 0.9977 | time: cuatro de la tarde, person: benito | time: cuatro de la tarde, event_name: reunión, person: benito |
| de-DE | errechne den zeitunterschied zwischen acht uhr dreißig g. t. m. und fünf uhr dreißig g. m. t. | datetime_convert | datetime_convert | 0.9346 | time: acht uhr dreißig, time_zone: g. t. m. | time: acht uhr dreißig g, time_zone: ., time: fünf uhr dreißig g. m. |
| de-DE | ausmachen von meinem wlan | iot_wemo_off | iot_wemo_off | 0.9862 | - | device_type: wlan |
| de-DE | spiel den beliebtesten song von annenmaykantereit | play_music | play_music | 0.9958 | - | artist_name: annenmaykantereit |
| fr-FR | que fait céline dion pour être belle | general_quirky | qa_factoid | 0.6343 | person: céline dion | person: céline dion |
| fr-FR | retrouvez les articles wapo du aujourd'hui sur trump | news_query | news_query | 0.9979 | media_type: wapo, date: aujourd'hui, news_topic: trump | date: aujourd'hui, news_topic: trump |
| fr-FR | la prochaine chanson jacques brel ne me quitte pas | play_music | play_music | 0.9929 | - | artist_name: jacques brel |
| ja-JP | 外は何度ですか | weather_query | weather_query | 0.9347 | weather_descriptor: 度 | - |
| ja-JP | 三月十五日の吉村との会議をリマインドする | calendar_set | calendar_set | 0.9995 | time: 三月十五日, person: 吉村, event_name: 会議 | date: 三月十五日の, person: 吉村, event_name: 会議 |
| ja-JP | カレンダーで今月のゴルフの予定をすべて削除する | calendar_remove | calendar_remove | 0.9993 | date: 月, event_name: ゴルフの予定 | date: 今月の, event_name: ゴルフの |
| hi-IN | कृपया खराब ग्राहक सेवा के लिए कॉमकास्ट करने के लिए एक शिकायत ट्वीट करें | social_post | social_post | 0.9998 | business_name: कॉमकास्ट, media_type: ट्वीट | media_type: ट्वीट |
| hi-IN | वॉल्यूम सेटिंग कहां है | audio_volume_other | music_query | 0.303 | - | - |
| hi-IN | आप अगले वर्ष नई दिल्ली में फेन फेस्ट के बारे में क्या जानते है | general_quirky | calendar_query | 0.8186 | date: अगले वर्ष, place_name: नई दिल्ली, event_name: फेन फेस्ट | date: अगले वर्ष, place_name: नई दिल्ली, event_name: फेन फेस्ट |
| ar-SA | يرجى وصف هذا الشيء بالنسبة لي | qa_definition | qa_definition | 0.9952 | - | definition_word: هذا |
| ar-SA | reason | play_podcasts | general_quirky | 0.8017 | podcast_name: reason | - |
| ar-SA | هل انت تشتغل في كارفور | general_quirky | qa_stock | 0.6865 | - | business_name: كارفور |
| sw-KE | olly ninunulie tiketi kwa jambojet ya kwenda nairobi wikendi hii | transport_ticket | transport_ticket | 0.9749 | transport_name: jambojet, place_name: nairobi | place_name: nairobi, date: wikendi hii |
| sw-KE | mfanyakazi wa kampuni yangu ana nambari ya simu ya nyumbani | email_querycontact | email_querycontact | 0.8624 | relation: mfanyakazi wa kampuni, personal_info: nambari ya simu ya nyumbani | relation: mfanyakazi wa kampuni, personal_info: nambari ya simu |
| sw-KE | ongeza ununuzi kwenye kalenda yangu ya kesho | calendar_set | calendar_set | 0.9991 | date: kesho | event_name: ununuzi, date: kesho |
| am-ET | ይህን ድገም | play_music | music_likeness | 0.1912 | - | - |
| am-ET | ነጠ ጫማ ወይም ጫማ በካልሲ ልልበስ | weather_query | takeaway_order | 0.3619 | weather_descriptor: ነጠ ጫማ ወይም ጫማ በካልሲ | weather_descriptor: ጫማ, weather_descriptor: ጫማ, business_name: በካልሲ |
| am-ET | የ ቀረጥ ዝርዝር ከ አስራ ዘጠኝ ዘጠና ጅምሮ አስወግድ | lists_remove | lists_remove | 0.9983 | list_name: ቀረጥ, date: አስራ ዘጠኝ ዘጠና | list_name: ቀረጥ |
| ta-IN | முட்டையை எவ்வளவு நேரம் வேக வைக்க வேண்டும் | cooking_recipe | cooking_recipe | 0.9936 | food_type: முட்டையை, cooking_type: வேக வைக்க | food_type: முட்டையை, cooking_type: வேக |
| ta-IN | இந்த வார இறுதியில் அணிவகுப்பு பற்றி மேலும் தெரிந்து கொள்ள வேண்டும் | general_quirky | calendar_query | 0.9775 | date: இந்த வார இறுதியில், event_name: அணிவகுப்பு | date: இந்த வார இறுதியில் |
| ta-IN | யாருக்கும் தெரியாது | play_music | play_music | 0.7684 | song_name: யாருக்கும் தெரியாது | - |
