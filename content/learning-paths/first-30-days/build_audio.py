from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parents[2]/'output'/'audio_scripts'
OUT.mkdir(parents=True,exist_ok=True)
combined=[]
for line in (ROOT/'audio_scenes.tsv').read_text().splitlines():
    num,speakers,scene=line.split('|');n=int(num)
    opening='Anlatıcı: NEXORA, 2.400 çalışanı ve 1,8 milyon müşterisi olan kurgusal bir fintech şirketi. Sen burada Junior GRC Specialist olarak çalışıyorsun. Bugün ekibin konuşmasını dinleyeceksin. Önünde bir ders anlatımı değil, karar bekleyen bir iş günü var. Söylenenlerin hangisi doğrulanmış bilgi, hangisi beklenti ya da varsayım? Konuşma sırasında buna dikkat et. Herkesin iyi niyeti olabilir; yine de farklı sorumluluklar ve zaman baskısı kararları zorlaştırabilir.'
    closing='Anlatıcı: Konuşma burada bitiyor. Şimdi bu iş gününün içine gireceksin. Karar verirken yalnız en hızlı seçeneği düşünme. Hangi bilginin eksik olduğunu, kararı kimin verebileceğini ve sonucun müşteriyi nasıl etkileyebileceğini de tart. Emin olmadığın noktayı açıkça söyleyebilirsin. Bir sonraki adımın, belirsizliği nasıl gidereceğini göstermeli. Ekipteki kişiler sonraki bölümlerde yeniden karşına çıkacak. Bugün oluşturduğun kayıtlar ve seçtiğin iletişim biçimi, bu ortak hikâyenin devamında önem taşıyacak. Hazırsan ilk duruma geç.'
    body=opening+'\n\n'+scene.replace('\\n','\n\n')+'\n\n'+closing
    words=len(body.split());seconds=round(words/115*60)
    assert 120<=seconds<=240,(n,words,seconds)
    text=f'Bölüm {n:02} — Intro kayıt metni\nquestion_id: grc-first30-q-{(n-1)*10+1:03} (kalıcı içerik kimliği; DB ID import registry içinde)\nKonuşmacılar: Anlatıcı, {speakers}\nTon: Doğal ofis konuşması. Anlatıcı sakin; Selin net ve destekleyici; Murat zaman baskısı altında; Ece kontrollü; Deniz kararlı; Arda krizde kısa ve odaklı; Ayşe sorgulayıcı.\nTahmini süre: {seconds//60}:{seconds%60:02} (115 kelime/dakika, duraklarla biraz uzayabilir)\nSabit dosya adı: grc_day_{n:02}.mp3\nBağlantı: AudioAsset.name_key=grc_day_{n:02}; yalnız bölümün ilk Question.intro alanı. Gerçek MP3 yüklenene kadar intro=NULL.\n\n{body}\n'
    (OUT/f'grc_day_{n:02}.txt').write_text(text)
    combined.append(text)
(OUT/'SES_KAYITLARI_TOPLU.md').write_text('# İlk 30 Gün — 10 Ses Kaydı\n\n'+'\n\n---\n\n'.join(combined))
print('10 intro metni; her biri 2–4 dakika.')
