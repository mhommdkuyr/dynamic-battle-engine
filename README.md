# Dynamic Battle Engine ⚡🥋
> **High-speed Combat Animation Engine & Framework inspired by *Combat Gods II* (03:10)**

![Combat Gods II Reference](https://img.shields.io/badge/Reference-Combat%20Gods%20II%20(03%3A10)-red)
![License](https://img.shields.io/badge/License-MIT-blue)
![Engines](https://img.shields.io/badge/Engines-Blender%20%7C%20OpenCV%20%7C%20Remotion-green)
![MCP Server](https://img.shields.io/badge/MCP-TypeScript%20%2F%20Vercel%20Ready-purple)

---

## 📖 Overview | نظرة عامة على المشروع

**Dynamic Battle Engine** هو محرك وإطار عمل مفتوح المصدر مصمم خصيصاً لإنتاج وإخراج مشاهد الأنيميشن القتالية فائقة السرعة، استناداً إلى المرجع الإخراجي والحركي الشهير في فيلم الأنيميشن **[Combat Gods II](https://youtu.be/XEtHpGSSTOU)** عند الدقيقة `03:10`.

يتميز المشروع بدمج تقنيات الإخراج الكلاسيكية والحديثة برمجياً:
1. **Smear Frames & Motion Elongation:** تشويه وتمديد الأطراف والكتل الهيكلية على طول متجهات السرعة اللحظية لتجسيد سرعة الضربات الخارقة.
2. **Action & Speed Lines:** خطوط حركة إشعاعية ومتجهة تركز عين المشاهد نحو بؤرة الاشتباك.
3. **Dynamic Trauma Camera:** نظام كاميرا فيزيائي يعتمد على التروما (Trauma Decay Model) للاهتزاز، الدوران الزاوي (Dutch Roll)، والتكبير الديناميكي (Zoom Punches).
4. **Impact Frames:** ومضات انحراف لوني وتعاكس ضوئي بالأبيض والأسود مع موجات صدمية (Shockwave rings) عند لحظة الاصطدام المباشر.
5. **Headless Blender Grease Pencil:** سكربت بايثون آلي لتجهيز مشاهد 2D داخل كاميرا وفضاء 3D بالكامل.
6. **Remotion & React Composition:** خط زمن ويب متطور لمعاينة المشاهد وتصييرها سحابياً.
7. **TypeScript MCP Server (Vercel Ready):** خادم Model Context Protocol جاهز للنشر كـ Serverless Function للتحكم في عمليات التحريك عن بعد.

---

## 🏗️ Architecture & Project Structure | هيكل المشروع

```
dynamic-battle-engine/
├── configs/
│   ├── engine_config.yaml             # إعدادات التصيير، دقة الشاشة، معاملات الاهتزاز والتمديد
│   └── combat_gods_scene_0310.json    # تصميم كوريغرافيا الاشتباك عند الدقيقة 03:10
├── src/
│   ├── core/
│   │   ├── camera.py                  # محاكي الكاميرا الفيزيائية والـ Trauma Shake
│   │   ├── fx_engine.py               # مولد Smear Frames و Action Lines و Impact Frames
│   │   └── timeline.py                # إدارة خط الزمن والأحداث الحركية
│   ├── engines/
│   │   ├── blender_grease_pencil.py   # مولد سكربتات Blender Headless Mode
│   │   └── opencv_renderer.py         # مصير بايثون المستقل فائق السرعة عبر OpenCV
│   ├── ai_pipeline/
│   │   └── pose_extractor.py          # واجهة استخراج الوضعيات (MimicMotion / DWPose)
│   ├── mcp_server/
│   │   ├── server.ts                  # خادم MCP الرسمي بلغة TypeScript
│   │   └── api_handler.ts             # Vercel Serverless Function Wrapper
│   └── remotion/
│       ├── Root.tsx                   # جذر تكوين Remotion
│       ├── CombatScene.tsx            # مشهد القتال المتزامن مع خط الزمن
│       └── components/
│           ├── ActionLines.tsx        # خطوط الحركة في Remotion
│           ├── ImpactFrame.tsx        # إطارات الصدمة العكسية
│           └── CameraShake.tsx        # محاكي اهتزاز الكاميرا
├── scripts/
│   ├── run_render.py                  # تشغيل التصيير الفوري وتوليد الفيديو
│   └── export_blender.py              # تصدير سكربت Blender الجاهز
├── tests/
│   └── test_engine.py                 # اختبارات الوحدات البرمجية
├── package.json                       # حزم Node.js و Remotion و MCP SDK
├── requirements.txt                   # مكتبات بايثون المطلوبة
└── tsconfig.json                      # إعدادات مترجم TypeScript
```

---

## 🚀 Quick Start | البدء السريع

### 1. تشغيل مصير البايثون المستقل (Headless OpenCV):
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# تشغيل تصيير المشهد التجريبي (1.5 ثانية بدقة 720p/1080p @ 60fps):
python3 scripts/run_render.py
```
المخرجات ستكون في المجلد `output/`:
- `output/combat_clash_0310.mp4` (الفيديو الكامل)
- `output/frame_018.png` (لقطة Clash Impact)
- `output/frame_060.png` (لقطة Recoil Kick)

### 2. تصدير وتشغيل Blender Grease Pencil:
```bash
python3 scripts/export_blender.py
# تشغيل بلندر في الوضع الصامت وتوليد المشهد:
blender -b -P scripts/blender_render.py
```

### 3. تشغيل Remotion Web Preview:
```bash
npm install
npm run remotion:preview
```

### 4. تشغيل خادم MCP TypeScript على Vercel:
الخادم جاهز للنشر المباشر في بيئة Vercel Serverless عبر `src/mcp_server/api_handler.ts`.
كما يمكن تشغيله محلياً عبر stdio لربطه مع محررات الذكاء الاصطناعي (Claude Desktop / Cursor):
```bash
npm run build
npm start
```
