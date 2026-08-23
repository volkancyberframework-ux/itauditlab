from .explanations import ANSWER_EXPLANATIONS


QUESTIONS = [
    (1, "Üniversite mezunu musun ya da olmayı planlıyor musun?", "", ["Evet", "Hayır"], "foundation"),
    (2, "İngilizce biliyor musun?", "Karşındakini teknik bir sohbette anlayıp cevap verebiliyor musun?", ["Evet", "Hayır"], "foundation"),
    (3, "CISA, CISSP gibi bağımsız (.org) sertifikalardan birine sahip misin veya hedefliyor musun?", "", ["Evet", "Hayır"], "foundation"),
    (4, "Detaycı mısın? Bundan keyif alıyor musun?", "", ["Evet", "Hayır"], "foundation"),
    (5, "Şüpheci misin? Bundan keyif alıyor musun?", "", ["Evet", "Hayır"], "foundation"),
    (6, "İşini kurallarına uygun yapar mısın?", "Yapmazsan hukuki sorumluluk doğurabileceğini biliyor musun?", ["Evet", "Hayır"], "foundation"),
    (7, "İnsanlara güvenir misin, yoksa kanıt mı ararsın?", "", ["Kanıt ararım", "Güvenirim"], "foundation"),
    (8, "Siber güvenlikte neden varsın?", "", ["Hacking terimlerinin havası için", "Bu işin gelecekteki kritik önemine inandığım için"], "foundation"),
    (9, "Yapay zekâ ve dijitalleşmenin gelecekte siber güvenlik iş gücüne daha fazla ihtiyaç doğuracağına inanıyor musun?", "", ["Evet", "Hayır"], "foundation"),
    (10, "Bir problemi çözerken sabırsızlanır mısın, yoksa sonuna kadar uğraşır mısın?", "", ["Sonuna kadar uğraşırım", "Sabırsızlanırım"], "orientation"),
    (11, "Karmaşık bir sistemde bütün resmi mi, bir parçayı mükemmel yapmayı mı tercih edersin?", "", ["Bütün resmi görmek", "Parçayı mükemmel yapmak"], "orientation"),
    (12, "Aynı anda birçok işi mi yürütürsün, tek bir işe mi odaklanırsın?", "", ["Çoklu görev (multitask)", "Tek iş odak"], "orientation"),
    (13, "Cihaz ayarlarını kurcalamaktan keyif alır mısın?", "", ["Evet", "Hayır"], "orientation"),
    (14, "Hatalı bir sistem görünce ‘bunu kim çözer?’ mi dersin, ‘nasıl çalışıyor?’u mu kurcalarsın?", "", ["Nasıl çalışıyor?", "Kim çözer?"], "orientation"),
    (15, "Terminal, komut satırı veya script yazmak seni korkutur mu, heyecanlandırır mı?", "", ["Heyecanlandırır", "Korkutur"], "orientation"),
    (16, "Bir açık bulsan ama duyurursan şirket zarar görecek olsa, ne yaparsın?", "", ["Bildiririm — sorumluluk", "Beklerim / gizlerim"], "orientation"),
    (17, "Başkalarının sana güvenmesi mi, sistemlerin sana güvenmesi mi daha önemli?", "", ["İnsanların bana güvenmesi", "Sistemlerin bana güvenmesi"], "orientation"),
    (18, "Hatalarını gizler misin, paylaşır mısın?", "", ["Paylaşırım — postmortem kültürü", "Gizlerim"], "orientation"),
    (19, "Uzun süre yalnız bilgisayar başında çalışmak seni rahatsız eder mi?", "", ["Hayır — rahatım", "Evet — zorlanırım"], "orientation"),
    (20, "Kritik anda biri bağırırsa panikler misin, sakin mi kalırsın?", "", ["Sakin kalırım", "Paniklerim"], "orientation"),
    (21, "Hata olduğunda kendini mi, sistemi mi suçlarsın?", "", ["Önce kendimi analiz ederim", "Sistemi suçlarım"], "orientation"),
    (22, "Yeni bir teknolojiyi görünce ‘tehlikeli’ mi, ‘öğrenilesi’ mi dersin?", "", ["Öğrenilesi", "Tehlikeli"], "orientation"),
    (23, "Para mı, anlam mı seni daha çok motive eder?", "", ["Anlam — etki", "Para — ödül"], "orientation"),
    (24, "5 yıl sonra bu sektörde nerede olmak istiyorsun?", "", ["Uzmanlıkta derinlik — teknik lider / uzman", "Yönetimde genişlik — CISO / GRC lideri"], "orientation"),
]

FOUNDATION_POSITIVE = {
    1: "Evet", 2: "Evet", 3: "Evet", 4: "Evet", 5: "Evet", 6: "Evet",
    7: "Kanıt ararım", 8: "Bu işin gelecekteki kritik önemine inandığım için", 9: "Evet",
}


def question_dicts():
    return [
        {
            "number": n,
            "text": text,
            "help": help_text,
            "options": options,
            "section": section,
            "explanations": ANSWER_EXPLANATIONS[n],
        }
        for n, text, help_text, options, section in QUESTIONS
    ]
