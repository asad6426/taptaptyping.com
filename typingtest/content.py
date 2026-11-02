"""
Starter practice words for development.

Status: UNREVIEWED. These lists were drafted by an AI assistant and have not been
checked by native speakers. They must be reviewed before they are presented as
reviewed content. See docs/typing-test/REVIEW_CHECKLIST.md.
"""

CONTENT_STATUS = 'unreviewed'
CONTENT_REVIEWED = False
CONTENT_VERSION = 'starter-1'

STARTER_WORDS = {
    'english': 'the people time water house school friend morning light small great often every little between work learn write read follow'.split(),
    'bengali': 'আমি তুমি আমরা বাংলা ভাষা মানুষ সময় পানি বাড়ি স্কুল বন্ধু সকাল আলো ছোট বড় কাজ শেখা লেখা পড়া দেশ'.split(),
    'hindi': 'मैं तुम हम भाषा लोग समय पानी घर स्कूल दोस्त सुबह रोशनी छोटा बड़ा काम सीखना लिखना पढ़ना देश क्षेत्र'.split(),
    'indonesian': 'saya kamu kami bahasa orang waktu air rumah sekolah teman pagi cahaya kecil besar kerja belajar menulis membaca negara selalu'.split(),
    'spanish': 'yo nosotros idioma gente tiempo agua casa escuela amigo mañana luz pequeño grande trabajo aprender escribir leer país también después'.split(),
    'portuguese': 'eu nós língua pessoas tempo água casa escola amigo manhã luz pequeno grande trabalho aprender escrever ler país também coração'.split(),
    'vietnamese': 'tôi chúng ngôn ngữ người thời gian nước nhà trường bạn sáng ánh nhỏ lớn công việc học viết đọc đất'.split(),
    'turkish': 'ben biz dil insan zaman su ev okul arkadaş sabah ışık küçük büyük iş öğrenmek yazmak okumak ülke şimdi güzel'.split(),
    'german': 'ich wir Sprache Menschen Zeit Wasser Haus Schule Freund Morgen Licht klein groß Arbeit lernen schreiben lesen Land schön für'.split(),
    'french': 'je nous langue gens temps eau maison école ami matin lumière petit grand travail apprendre écrire lire pays très après'.split(),
    'arabic': 'أنا نحن لغة ناس وقت ماء بيت مدرسة صديق صباح نور صغير كبير عمل تعلم كتابة قراءة بلد جميل كتاب'.split(),
    'russian': 'я мы язык люди время вода дом школа друг утро свет маленький большой работа учить писать читать страна хорошо всегда'.split(),
    'thai': 'ฉัน เรา ภาษา คน เวลา น้ำ บ้าน โรงเรียน เพื่อน เช้า แสง เล็ก ใหญ่ งาน เรียน เขียน อ่าน ประเทศ ดี เสมอ'.split(),
    'urdu': 'میں ہم زبان لوگ وقت پانی گھر اسکول دوست صبح روشنی چھوٹا بڑا کام سیکھنا لکھنا پڑھنا ملک اچھا کتاب'.split(),
    'italian': 'io noi lingua persone tempo acqua casa scuola amico mattina luce piccolo grande lavoro imparare scrivere leggere paese più perché'.split(),
    'polish': 'ja my język ludzie czas woda dom szkoła przyjaciel rano światło mały duży praca uczyć pisać czytać kraj dobrze zawsze'.split(),
    'dutch': 'ik wij taal mensen tijd water huis school vriend ochtend licht klein groot werk leren schrijven lezen land altijd mooi'.split(),
    'filipino': 'ako tayo wika tao oras tubig bahay paaralan kaibigan umaga ilaw maliit malaki trabaho matuto sumulat magbasa bansa palagi maganda'.split(),
    'japanese': 'わたし ことば ひと じかん みず いえ がっこう ともだち あさ ひかり ちいさい おおきい しごと まなぶ かく よむ くに いつも きれい ほん'.split(),
    'korean': '나는 우리 언어 사람 시간 물 집 학교 친구 아침 빛 작은 큰 일 배우다 쓰다 읽다 나라 항상 좋은'.split(),
}

# Each language has four original sentences. Short uses the first, Medium the
# first two, and Long all four. Same review status as the word lists: UNREVIEWED.
STARTER_PARAGRAPHS = {
    'english': [
        'A short walk in the morning can change the mood of a whole day.',
        'The streets are quiet, the air is cool, and there is time to think.',
        'Many people find that their best ideas arrive when they stop looking for them.',
        'So tomorrow, leave your phone at home and see where the road takes you.',
    ],
    'bengali': [
        'সকালের একটু হাঁটা সারা দিনের মন ভালো করে দিতে পারে।',
        'রাস্তা তখন শান্ত থাকে, বাতাস ঠান্ডা থাকে, আর ভাবার সময় পাওয়া যায়।',
        'অনেকেই দেখেন যে ভালো ভাবনাগুলো হঠাৎ করেই মাথায় আসে।',
        'তাই কাল সকালে ফোনটা ঘরে রেখে একটু বাইরে ঘুরে আসুন।',
    ],
    'hindi': [
        'सुबह की छोटी सी सैर पूरे दिन का मन बदल सकती है।',
        'सड़कें शांत होती हैं, हवा ठंडी होती है और सोचने का समय मिलता है।',
        'बहुत से लोगों को अच्छे विचार तभी आते हैं जब वे उन्हें खोजना छोड़ देते हैं।',
        'इसलिए कल अपना फ़ोन घर पर छोड़िए और देखिए कि रास्ता कहाँ ले जाता है।',
    ],
    'indonesian': [
        'Jalan kaki sebentar di pagi hari dapat mengubah suasana hati seharian.',
        'Jalanan masih sepi, udaranya sejuk, dan ada waktu untuk berpikir.',
        'Banyak orang mendapat ide terbaik justru saat mereka berhenti mencarinya.',
        'Jadi besok, tinggalkan ponsel di rumah dan lihat ke mana jalan membawa Anda.',
    ],
    'spanish': [
        'Un paseo corto por la mañana puede cambiar el ánimo de todo el día.',
        'Las calles están tranquilas, el aire es fresco y hay tiempo para pensar.',
        'Muchas personas descubren que sus mejores ideas llegan cuando dejan de buscarlas.',
        'Así que mañana deja el teléfono en casa y mira adónde te lleva el camino.',
    ],
    'portuguese': [
        'Uma caminhada curta pela manhã pode mudar o humor do dia inteiro.',
        'As ruas estão calmas, o ar é fresco e há tempo para pensar.',
        'Muitas pessoas descobrem que as melhores ideias chegam quando param de procurá-las.',
        'Por isso, amanhã deixe o telefone em casa e veja aonde o caminho leva você.',
    ],
    'vietnamese': [
        'Một chuyến đi bộ ngắn vào buổi sáng có thể thay đổi tâm trạng cả ngày.',
        'Đường phố yên tĩnh, không khí mát mẻ và có thời gian để suy nghĩ.',
        'Nhiều người nhận ra ý tưởng hay nhất đến khi họ ngừng tìm kiếm.',
        'Vì vậy, ngày mai hãy để điện thoại ở nhà và xem con đường đưa bạn đến đâu.',
    ],
    'turkish': [
        'Sabahları kısa bir yürüyüş bütün günün havasını değiştirebilir.',
        'Sokaklar sessizdir, hava serindir ve düşünmek için zaman vardır.',
        'Birçok insan en iyi fikirlerin onları aramayı bıraktığında geldiğini fark eder.',
        'Bu yüzden yarın telefonunu evde bırak ve yolun seni nereye götürdüğünü gör.',
    ],
    'german': [
        'Ein kurzer Spaziergang am Morgen kann die Stimmung des ganzen Tages verändern.',
        'Die Straßen sind ruhig, die Luft ist kühl, und es bleibt Zeit zum Nachdenken.',
        'Viele Menschen merken, dass die besten Ideen kommen, wenn sie nicht mehr danach suchen.',
        'Lass also morgen dein Telefon zu Hause und sieh, wohin dich der Weg führt.',
    ],
    'french': [
        'Une courte promenade le matin peut changer l’humeur de toute la journée.',
        'Les rues sont calmes, l’air est frais et l’on a le temps de réfléchir.',
        'Beaucoup de gens découvrent que leurs meilleures idées arrivent quand ils cessent de les chercher.',
        'Alors demain, laissez votre téléphone à la maison et voyez où mène le chemin.',
    ],
    'arabic': [
        'يمكن لنزهة قصيرة في الصباح أن تغير مزاج اليوم كله.',
        'تكون الشوارع هادئة، والهواء باردًا، ويوجد وقت للتفكير.',
        'يكتشف كثير من الناس أن أفضل الأفكار تأتي عندما يتوقفون عن البحث عنها.',
        'لذلك اترك هاتفك في البيت غدًا وانظر إلى أين يأخذك الطريق.',
    ],
    'russian': [
        'Короткая утренняя прогулка может изменить настроение на весь день.',
        'На улицах тихо, воздух прохладный, и есть время подумать.',
        'Многие замечают, что лучшие идеи приходят, когда перестаёшь их искать.',
        'Поэтому завтра оставьте телефон дома и посмотрите, куда приведёт дорога.',
    ],
    'thai': [
        'การเดินสั้นๆ ในตอนเช้าสามารถเปลี่ยนอารมณ์ของคุณได้ทั้งวัน',
        'ถนนเงียบสงบ อากาศเย็นสบาย และมีเวลาให้คิด',
        'หลายคนพบว่าความคิดที่ดีที่สุดมักมาเมื่อเลิกค้นหา',
        'พรุ่งนี้ลองวางโทรศัพท์ไว้ที่บ้าน แล้วดูว่าถนนจะพาคุณไปที่ไหน',
    ],
    'urdu': [
        'صبح کی ایک مختصر سیر پورے دن کا مزاج بدل سکتی ہے۔',
        'سڑکیں پرسکون ہوتی ہیں، ہوا ٹھنڈی ہوتی ہے اور سوچنے کا وقت ملتا ہے۔',
        'بہت سے لوگ دیکھتے ہیں کہ بہترین خیالات تب آتے ہیں جب وہ انہیں ڈھونڈنا چھوڑ دیتے ہیں۔',
        'اس لیے کل اپنا فون گھر پر چھوڑیں اور دیکھیں کہ راستہ آپ کو کہاں لے جاتا ہے۔',
    ],
    'italian': [
        'Una breve passeggiata al mattino può cambiare l’umore di tutta la giornata.',
        'Le strade sono tranquille, l’aria è fresca e c’è tempo per pensare.',
        'Molte persone scoprono che le idee migliori arrivano quando smettono di cercarle.',
        'Perciò domani lascia il telefono a casa e guarda dove ti porta la strada.',
    ],
    'polish': [
        'Krótki poranny spacer może zmienić nastrój na cały dzień.',
        'Ulice są ciche, powietrze chłodne i jest czas na myślenie.',
        'Wiele osób zauważa, że najlepsze pomysły przychodzą, gdy przestają ich szukać.',
        'Dlatego jutro zostaw telefon w domu i zobacz, dokąd zaprowadzi cię droga.',
    ],
    'dutch': [
        'Een korte wandeling in de ochtend kan de stemming van de hele dag veranderen.',
        'De straten zijn rustig, de lucht is koel en er is tijd om na te denken.',
        'Veel mensen merken dat de beste ideeën komen als ze er niet meer naar zoeken.',
        'Laat dus morgen je telefoon thuis en kijk waar de weg je brengt.',
    ],
    'filipino': [
        'Ang maikling lakad sa umaga ay maaaring magpabago ng pakiramdam sa buong araw.',
        'Tahimik ang mga kalye, malamig ang hangin, at may oras para mag-isip.',
        'Maraming tao ang nakakapansin na dumarating ang pinakamagagandang ideya kapag tumigil na silang maghanap.',
        'Kaya bukas, iwan ang iyong telepono sa bahay at tingnan kung saan ka dadalhin ng daan.',
    ],
    'japanese': [
        'あさのみじかいさんぽは、いちにちのきぶんをかえることがあります。',
        'みちはしずかで、くうきはすずしく、かんがえるじかんがあります。',
        'よいかんがえは、さがすのをやめたときにうかぶことがおおいです。',
        'あしたはでんわをいえにおいて、みちのさきへあるいてみましょう。',
    ],
    'korean': [
        '아침의 짧은 산책은 하루의 기분을 바꿀 수 있습니다.',
        '거리는 조용하고 공기는 시원하며 생각할 시간이 있습니다.',
        '많은 사람들은 찾기를 멈출 때 좋은 생각이 떠오른다는 것을 알게 됩니다.',
        '그러니 내일은 전화기를 집에 두고 길이 어디로 이어지는지 걸어 보세요.',
    ],
}
