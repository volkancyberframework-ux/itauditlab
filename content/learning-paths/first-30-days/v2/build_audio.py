"""Create synthetic Turkish dialogue recordings using installed system voices."""
import subprocess,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
OUT=REPO/'mobile_api'/'demo_assets'/'first30_v2'
TMP=Path('/tmp/first30-audio');TMP.mkdir(exist_ok=True)
ROLES={'Selin':'yöneticin','Murat':'IT operasyon müdürü','Deniz':'bilgi güvenliği yöneticisi','Ece':'risk müdürü','Arda':'SOC ekip lideri','Ayşe':'genel müdür'}
report=[]
for n in range(1,11):
    source=(REPO/'output'/'audio_scripts'/f'grc_day_{n:02}.txt').read_text()
    body=source[source.index('Anlatıcı:'):].strip()
    chunks=[c.strip() for c in body.split('\n\n') if c.strip()]
    wavs=[];transcript=[]
    for i,chunk in enumerate(chunks):
        speaker,text=chunk.split(':',1)
        voice='Cem (Enhanced)' if speaker in ('Murat','Deniz','Arda') else 'Yelda'
        # Speaker labels are spoken at the start so roles remain clear without captions.
        spoken=(f'{speaker}, {ROLES[speaker]}. ' if speaker in ROLES else '')+text.strip()
        aiff=TMP/f'{n:02}_{i:02}.aiff';wav=TMP/f'{n:02}_{i:02}.wav'
        subprocess.run(['/usr/bin/say','-v',voice,'-r','125','-o',str(aiff),spoken],check=True)
        subprocess.run(['ffmpeg','-loglevel','error','-y','-i',str(aiff),'-ar','24000','-ac','1','-c:a','pcm_s16le',str(wav)],check=True)
        wavs.append(wav);transcript.append(f'{speaker}: {text.strip()}')
    concat=TMP/f'concat_{n:02}.txt';concat.write_text(''.join(f"file '{p}'\n" for p in wavs))
    output=OUT/f'grc_day_{n:02}.mp3'
    subprocess.run(['ffmpeg','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c:a','libmp3lame','-b:a','96k',str(output)],check=True)
    probe=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(output)])
    duration=float(json.loads(probe)['format']['duration'])
    assert duration>45 and output.stat().st_size>10000
    (ROOT/f'transcript_{n:02}.txt').write_text('\n\n'.join(transcript))
    report.append(dict(file=output.name,seconds=round(duration,2),bytes=output.stat().st_size,synthetic=True,voices=['Yelda','Cem (Enhanced)']))
    print(f'{output.name}: {duration:.1f}s',flush=True)
(ROOT/'audio_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
