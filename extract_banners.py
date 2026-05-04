# extract_banners.py — MP4 → JPG + GIF batch exporter
# Run once locally: python extract_banners.py

import subprocess
import re
from io import BytesIO
from pathlib import Path
from PIL import Image

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG = "ffmpeg"

DOWNLOADS   = Path("C:/Users/ALP/Downloads")
BANNERS     = Path("C:/Users/ALP/Desktop/ascelia-bot-main/assets/banners")
SIZE        = (638, 159)
N_GIF       = 24
DURATION_MS = 83
STATIC_PCT  = 0.30  # karedeki anı video süresinin %30'u

# (mp4_dosya_adi_prefixe, cikti_id)
WALLPAPERS = [
    ("2b-in-the-field-of-blue-lilies-nier-automata-moewalls-com",                   "2b"),
    ("acheron-crimson-lotus-honkai-star-rail-moewalls-com",                          "acheron"),
    ("angel-devil-chainsaw-man-moewalls-com",                                        "angel_devil"),
    ("azure-blade-moewalls-com",                                                     "azure_blade"),
    ("black-clover-nacht-faust-moewalls-com",                                        "nacht"),
    ("blue-horizon-wandering-witch-the-journey-of-elaina-moewalls-com",              "elaina"),
    ("chisa-nerd-wuthering-waves-moewalls-com",                                      "chisa"),
    ("chromatic-tears-moewalls-com",                                                 "chromatic"),
    ("columbina-dark-angel-genshin-impact-moewalls-com",                             "columbina"),
    ("crimson-kitsune-moewalls-com",                                                 "crimson_kitsune"),
    ("fiery-anime-eyes-moewalls-com",                                                "fiery_eyes"),
    ("future-trunks-powering-up-dragon-ball-moewalls-com",                           "trunks"),
    ("galbrena-dual-flame-eyes-awakening-wuthering-waves-moewalls-com",              "galbrena"),
    ("gojo-hollow-purple-unlimited-void-jujutsu-kaisen-moewalls-com",                "gojo_hollow"),
    ("goku-shadow-sunset-dragon-ball-moewalls-com",                                  "goku"),
    ("gugu-gaga-sleepy-river-moewalls-com",                                          "gugu_gaga"),
    ("hoshimi-miyabi-ultimate-zenless-zone-zero-moewalls-com",                       "miyabi"),
    ("itachi-sharingan-lightning-moewalls-com",                                      "itachi"),
    ("kitsune-ronin-moewalls-com",                                                   "kitsune_ronin"),
    ("lucy-blossom-samurai-cyberpunk-edgerunners-moewalls-com",                      "lucy"),
    ("mahoraga-x-megumi-jujutsu-kaisen-moewalls-com",                                "mahoraga"),
    ("makima-chainsaw-man-moewalls-com",                                             "makima"),
    ("miku-starlight-idol-vocaloid-moewalls-com",                                    "miku"),
    ("musashi-soul-of-the-katana-vagabond-moewalls-com",                             "musashi"),
    ("oni-girl-tattoos-moewalls-com",                                                "oni_girl"),
    ("oni-mask-yakuza-moewalls-com",                                                 "oni_mask"),
    ("phainon-cosmic-divinity-honkai-star-rail-moewalls-com",                        "phainon"),
    ("pokemon-leafeaon-and-espeon-forest-moewalls-com",                              "leafeon"),
    ("saber-excalibur-fate-stay-night-moewalls-com",                                 "saber"),
    ("sakura-blade-maiden-moewalls-com",                                             "sakura_blade"),
    ("squishy-hoshino-blue-archive-moewalls-com",                                    "hoshino"),
    ("the-herta-honkai-star-rail-moewalls-com",                                      "herta"),
    ("the-scarlet-devil-moewalls-com",                                               "scarlet_devil"),
    ("trunks-super-saiyan-rage-dragon-ball-moewalls-com",                            "trunks_rage"),
    ("vagabond-samurai-waves-moewalls-com",                                          "vagabond"),
    ("wuthering-waves-zhixing-moewalls-com",                                         "zhixing"),
    ("zhuang-fangyi-between-mountains-and-rivers-arknights-endfield-moewalls-com",   "zhuang"),
]


def get_duration(mp4: Path) -> float:
    result = subprocess.run(
        [FFMPEG, "-i", str(mp4)],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", result.stderr)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return 10.0


def extract_frame(mp4: Path, timestamp: float) -> Image.Image:
    result = subprocess.run([
        FFMPEG, "-y",
        "-ss", f"{timestamp:.3f}",
        "-i", str(mp4),
        "-frames:v", "1",
        "-vf", f"scale={SIZE[0]}:{SIZE[1]}:force_original_aspect_ratio=increase,crop={SIZE[0]}:{SIZE[1]}",
        "-f", "image2pipe", "-vcodec", "png", "pipe:1",
    ], capture_output=True)
    return Image.open(BytesIO(result.stdout)).convert("RGB")


def process(mp4: Path, out_id: str):
    jpg_out = BANNERS / f"{out_id}.jpg"
    gif_out = BANNERS / f"{out_id}.gif"

    if jpg_out.exists() and gif_out.exists():
        print(f"  ATLANDI (mevcut): {out_id}")
        return

    if not mp4.exists():
        print(f"  BULUNAMADI: {mp4.name}")
        return

    dur = get_duration(mp4)
    print(f"  {out_id}: {dur:.1f}s  ->  ", end="", flush=True)

    # Statik kare
    static_img = extract_frame(mp4, dur * STATIC_PCT)
    static_img.save(str(jpg_out), "JPEG", quality=90)

    # Animasyonlu GIF
    timestamps  = [dur * i / N_GIF for i in range(N_GIF)]
    gif_frames  = [extract_frame(mp4, t) for t in timestamps]
    gif_frames[0].save(
        str(gif_out), save_all=True, append_images=gif_frames[1:],
        loop=0, duration=DURATION_MS, optimize=True,
    )

    print(f"jpg {jpg_out.stat().st_size//1024}KB  gif {gif_out.stat().st_size//1024}KB")


if __name__ == "__main__":
    BANNERS.mkdir(parents=True, exist_ok=True)
    print(f"FFmpeg: {FFMPEG}")
    print(f"Cikti: {BANNERS}\n")
    for prefix, out_id in WALLPAPERS:
        mp4 = DOWNLOADS / f"{prefix}.mp4"
        process(mp4, out_id)
    print("\nTamamlandi!")
