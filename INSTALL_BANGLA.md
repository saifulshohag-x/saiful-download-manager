# Saiful Download Manager — ইনস্টলেশন গাইড (বাংলা)

**Saiful Download Manager** — Python দিয়ে তৈরি IDM-এর মতো হাই-স্পিড ডাউনলোড ম্যানেজার। Windows 10/11 64-bit এর জন্য।

## মূল ফিচার

- ১৬-সেগমেন্ট parallel download (IDM-এর মতো)
- স্বয়ংক্রিয় ব্রাউজার এক্সটেনশন ইনস্টল (Chrome, Edge, Brave, Opera, Firefox)
- Pause / Resume (যেকোনো সময়)
- Video Grabber (YouTube, Facebook, TikTok, ইত্যাদি)
- ডাউনলোড স্পিড IDM-এর সমতুল্য
- সম্পূর্ণ ফ্রি, কোনো লাইসেন্স নেই

## ৩টি উপায়ে .exe পাওয়া যায়

### উপায় ১ — নিজের পিসিতে বানান (সবচেয়ে দ্রুত, ৫ মিনিট)

1. Python 3.10+ ইনস্টল করুন — https://python.org থেকে
   - ইনস্টল করার সময় **"Add Python to PATH"** অপশনে অবশ্যই টিক দিন
2. এই ফোল্ডারটি যেকোনো জায়গায় রাখুন (যেমন `C:\SaifulDownloadManager`)
3. `build_exe.bat` ফাইলে ডাবল-ক্লিক করুন
4. ৩-৫ মিনিট অপেক্ষা করুন
5. তৈরি হবে: `dist\SaifulDownloadManager.exe` (~৭০ MB)
6. এই `.exe` ফাইলটি যেকোনো Windows 10/11 64-bit পিসিতে চালানো যাবে — Python লাগবে না

### উপায় ২ — সরাসরি Python দিয়ে চালানো

```
pip install -r requirements.txt
python main.py
```

### উপায় ৩ — GitHub Actions দিয়ে অটো-বিল্ড (ফ্রি)

1. এই ফোল্ডারটি একটি নতুন GitHub repository তে push করুন
2. GitHub-এর **Actions** tab এ যান → "Build Windows EXE" workflow অটো চলবে
3. ৫-১০ মিনিট পরে workflow-এর artifact থেকে `SaifulDownloadManager.exe` ডাউনলোড করুন
4. Release তৈরি করতে: `git tag v1.0.0 && git push --tags` — GitHub অটোমেটিক release প্রকাশ করবে

## প্রথমবার চালালে যা হবে

১. অ্যাপ চালু হবে
২. ব্যাকগ্রাউন্ডে ইনস্টল করা ব্রাউজার গুলো detect হবে (Chrome, Edge, Brave, Opera, Firefox)
৩. প্রতিটি ব্রাউজারে অটো extension install হবে:
   - `%LOCALAPPDATA%\SaifulDownloadManager\extension` ফোল্ডারে extension কপি হবে
   - Chrome/Edge/Brave/Opera: `Preferences` JSON এডিট করে extension register করবে
   - Firefox: Windows Registry তে `.xpi` register করবে
৪. ব্রাউজার restart করলে extension লোড হবে
৫. Chrome/Edge একবার "Disable developer mode extensions" warning দেখাতে পারে — **Keep** ক্লিক করুন

## ব্যবহার

- **+ Add URL** বাটনে URL দিন → ডাউনলোড শুরু
- প্রতিটি ডাউনলোডে **Pause / Resume / Stop / X / Open** বাটন
- **Resume All / Pause All / Stop All** দিয়ে batch control
- **Video Grabber** দিয়ে YouTube ভিডিও
- **Options** এ সব সেটিংস
- বাম পাশে category: All / Downloading / Queued / Finished

## ফাইল কোথায় সেভ হবে?

ডিফল্ট: `C:\Users\<আপনার-নাম>\Downloads\`
Options এ গিয়ে পরিবর্তন করা যাবে।

## সমস্যা হলে

- **"pip is not recognized"** → Python install করার সময় "Add to PATH" টিক দেননি
- **Extension লোড হচ্ছে না** → Browser restart করুন। অ্যাপের "Browser Ext" বাটনে ক্লিক করে আবার install করুন
- **YouTube ডাউনলোড হচ্ছে না** → `pip install -U yt-dlp` দিয়ে আপডেট করুন
- **"Disable developer mode extensions" warning** → **Keep** ক্লিক করুন

## Settings ফাইল

সব সেটিংস: `C:\Users\<আপনার-নাম>\.saiful_dm\config.json`
Extension ফাইল: `C:\Users\<আপনার-নাম>\AppData\Local\SaifulDownloadManager\extension\`

## License

MIT — সম্পূর্ণ ফ্রি, পরিবর্তন ও বিতরণ করতে পারবেন।
