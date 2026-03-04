# Faz 6: Tenant Frontend Uygulaması

**Faz Başlığı:** Tenant Uygulama Arayüzü — Membro Dashboard & Chat Deneyimi  
**Bağımlılıklar:** Faz 1–5 (tüm backend API'ler hazır)  
**Tech Stack:** Next.js 16.1 + TypeScript + Tailwind CSS (App Router)  
**Kapsam:** Login sonrası tenant'a özel uygulama — `{tenant}.themembro.com/`

> **Son güncelleme:** 2026-03-04

---

## 1. Araştırma Temeli: 2026 UX/UI Trendleri

Bu doküman oluşturulurken Fuselab Creative, JetBase ve Smashing Magazine kaynaklı 2026 SaaS tasarım araştırmaları incelendi. Temel bulgular şunlar:

| Trend | Kaynaklar | Membro'ya Etki |
|---|---|---|
| **Dark Mode as Standard** | Fuselab, JetBase | Varsayılan koyu tema; açık tema toggle opsiyonel |
| **Liquid Glass Aesthetics** | Fuselab | Modal, panel ve card'larda frosted-glass efekti |
| **AI-First Conversational UI** | Fuselab, JetBase | Chat ekranı uygulamanın çekirdeği |
| **Minimalism + Purposeful Whitespace** | JetBase, Smashing | Sidebar sade, içerik alanı nefes alır |
| **Micro-interactions** | JetBase | Buton feedback, kart hover, loading state'leri |
| **Data-Driven / Proactive Insights** | Fuselab | Dashboard'da AI üretilen aksiyon önerileri |
| **AI-Driven Personalization** | Fuselab, JetBase | Sidebar sıralaması kullanım frekansına göre |
| **Cross-Platform Consistency** | Fuselab | Mobile-responsive, tablet-first layout |
| **Emotional Design** | JetBase | Membro kişilikleri avatar ve renk ile temsil edilir |
| **Feedback Loops** | JetBase | Her AI aksiyonunda anlık durum göstergesi |

### Tasarım Felsefesi

> **"Araç hissi değil, asistan hissi."**

Membro bir yazılım paneli değil, kullanıcının dijital ekibi. Arayüz bu ekiple iletişimi kolaylaştırmalı; ekranlar sade, odak noktası her zaman "aktif membro" olmalı. Karmaşıklık gizlenmez — katmanlanır (progressive disclosure).

---

## 2. Tasarım Sistemi

### 2.1 Renk Paleti (Design Tokens)

### Brand Core
```css
--color-brand-navy:       #180942   /* Ana marka rengi — başlık, koyu bg, footer */
--color-brand-coral:      #FF6F80   /* Açık bg üzerinde birincil CTA, error */
--color-brand-lime:       #D2F76C   /* Koyu bg üzerinde birincil CTA, success */
--color-brand-periwinkle: #655F9C   /* İkincil metin, border */
```

### Surface Scale
```css
--color-surface-0:        #FAF9FF   /* Ana sayfa arka planı */
--color-surface-50:       #F0ECFF   /* Alternatif section bg */
--color-surface-100:      #E4DEFF   /* Kart border, ayraç */
--color-surface-200:      #CBC1F0   /* Vurgu border */
--color-surface-800:      #231263   /* Koyu section ara tonu */
--color-surface-900:      #180942   /* Koyu section bg (brand-navy ile aynı) */
```

### Text Tokens
```css
--color-text-primary:          #180942   /* Ana metin (açık zemin) */
--color-text-secondary:        #655F9C   /* İkincil metin (açık zemin) */
--color-text-tertiary:         #9590C4   /* Üçüncül / placeholder */
--color-text-on-dark:          #EAE6FF   /* Koyu bg üzerinde ana metin */
--color-text-on-dark-secondary:#A39DC6   /* Koyu bg üzerinde ikincil metin */
```

### Semantic Colors
```css
--color-success:          #D2F76C   /* Success state (brand-lime) */
--color-error:            #FF6F80   /* Error state (brand-coral) */
--color-info:             #655F9C   /* Info state (brand-periwinkle) */
--color-warning:          #F5C842   /* Warning state */
```

### Background Utilities
```css
--background:             #FAF9FF   /* Root background (surface-0) */
--foreground:             #180942   /* Root foreground (brand-navy) */
```

### 2.2 Tipografi

| Rol | Font | Boyut / Weight |
|-----|------|----------------|
| **Display** | Plus Jakarta Sans | 36–48px / 700–800 |
| **Hero Heading** | Plus Jakarta Sans | 30–36px / 700–800 |
| **Section Heading** | Plus Jakarta Sans | 20–24px / 700 |
| **Subsection Heading** | Plus Jakarta Sans | 18–20px / 600–700 |
| **Body Large** | Plus Jakarta Sans | 18px / 400–500 |
| **Body** | Plus Jakarta Sans | 16px / 400 |
| **Body Small** | Plus Jakarta Sans | 14px / 400 |
| **Caption / Label** | Plus Jakarta Sans | 12px / 500–600 |

#### Tailwind Utility Mapping
```
text-xs   : 12px   (Caption, label, badge)
text-sm   : 14px   (Body small, secondary text)
text-base : 16px   (Primary body text)
text-lg   : 18px   (Large body, subheading)
text-xl   : 20px   (Section subheading)
text-2xl  : 24px   (Section heading)
text-3xl  : 30px   (Hero heading mobile)
text-4xl  : 36px   (Hero heading tablet/desktop)
text-5xl  : 48px   (Display text, hero impact)
```

#### Weight Scale
```
font-light       : 300
font-normal      : 400
font-medium      : 500
font-semibold    : 600
font-bold        : 700
font-extrabold   : 800
font-black       : 900 (MemberAvatar initials)
```

---

### 2.3 Spacing & Radius

#### Border Radius
```css
--radius-sm:     4px     /* Focus ring, helper element */
--radius-md:     8px     /* Input, small card */
--radius-lg:     12px    /* General card, panel */
--radius-xl:     16px    /* Large card, modal */
--radius-2xl:    24px    /* Showcase panel, büyük blok */
--radius-full:   9999px  /* Pill badge, avatar */
```

#### Tailwind Radius Hiyerarşisi (Actual Usage)
```
rounded-xl       : 12px   (Genel kart, form input, toggle, chip, ikon bg)
rounded-2xl      : 24px   (Panel, showcase, büyük blok)
rounded-full     : 9999px (Pill badge, avatar, circular element)
```

#### Spacing Unit: 8pt Grid
```
4px base scale  : 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64 / 80 / 96 / 128
Tailwind mapping: 1 / 2 / 3  / 4  / 5  / 6  / 8  / 10 / 12 / 16 / 20 / 24 / 32
```

---

### 2.5 Animasyon Sistemi

#### Mount / Entrance (Framer Motion)
```typescript
const FADE_UP = {
  hidden: { opacity: 0, y: 24 },
  visible: (delay = 0) => ({ 
    opacity: 1, 
    y: 0, 
    transition: { duration: 0.5, delay } 
  }),
};
```

#### Sürekli / Döngüsel (CSS Keyframes)
```css
@keyframes marquee       /* Yatay kayan metin bandı */
@keyframes fade-in       /* Mount sırasında opaklık girişi */
@keyframes slide-up      /* Mount sırasında yukarı kayma */
@keyframes float-a/b/c/d /* Hero'daki agent kartlarının yüzme animasyonu */
@keyframes pulse-ring    /* Aktif agent merkez halkası */
@keyframes flow-dash     /* SVG çizgi akış animasyonu */
```

---

### 2.6 Dark Mode / Section Alternation

#### Anasayfa Section Pattern
```
surface-0 ↔ surface-50 (açık section'lar dönüşümlü)
surface-900 (koyu section'lar: SloganBridgeSection, DramaSection)
```

#### Koyu Zemin Üzerinde Metin
```
text-on-dark           : #EAE6FF (Başlık, primary)
text-on-dark-secondary : #A39DC6 (Açıklama, secondary)
brand-lime             : #D2F76C (Koyu zemin CTA)
brand-coral            : #FF6F80 (Aksan kelime)
```

---

### 2.5 Elevations & Glass Effect

`backdrop-filter: blur(16px) saturate(180%)` + `bg-glass` token → Modal, üst bar, floating panel.

Solid shadow yerine Liquid Glass tercih edilir. Card'larda `box-shadow: 0 1px 2px rgba(0,0,0,0.5)`.

### 2.6 Motion Principles

| Durum | Easing | Süre |
|---|---|---|
| Page transition | `ease-out` | 200ms |
| Modal open/close | `spring(stiffness:300, damping:30)` | — |
| Sidebar collapse | `ease-in-out` | 180ms |
| Micro-interaction (hover, click) | `ease-out` | 80–120ms |
| Skeleton → content | `ease-in` fade | 250ms |

Framer Motion kullanılır. `AnimatePresence` ile sayfa ve modal geçişleri yönetilir.

---

### Uygulama Kuralları

#### ❌ Yasaklar
```tsx
// Ham hex className'de
className="hover:bg-[#ff5268]"

// Tailwind ölçeğinde ≤4px uzaklıkta eşdeğer varsa arbitrary
className="text-[13px]"

// Dar container (genel sayfalarda)
className="max-w-3xl px-4"

// Hiyerarşi dışı radius
className="rounded-3xl"
```

#### ✅ Doğru Kullanım
```tsx
// Token + opacity
className="hover:bg-brand-coral/90"

// Tailwind utility
className="text-xs"

// Standart container
className="max-w-[1320px] px-6 lg:px-10"

// Hiyerarşiye uygun radius
className="rounded-xl"
className="rounded-2xl"

// Runtime dinamik değer
style={{ backgroundColor: member.accentColor }}
```

---

## 3. Layout Mimarisi

### 3.1 Ana Shell

```
┌─────────────────────────────────────────────────┐
│  TopBar (48px, glass)                           │
│  [Logo] · [tenant adı]          [notifications] [avatar] │
├──────────┬──────────────────────────────────────┤
│          │                                      │
│ Sidebar  │  <Page Content>                      │
│ (240px)  │                                      │
│          │                                      │
│ collapsed│                                      │
│ (60px)   │                                      │
│          │                                      │
└──────────┴──────────────────────────────────────┘
```

**Sidebar davranışı:**
- Masaüstü: 240px genişlikte açık (collapsed toggle ile 60px'e iner)
- Tablet: Varsayılan collapsed
- Mobil: Drawer (overlay) olarak açılır

### 3.2 Sidebar Yapısı

```
──────────────────
  ⊕  Dashboard           ← Nav item (icon + label)
  ⊡  Membros
  ◎  Knowledge           ← (Faz 6.x, placeholder)
  ◷  Meetings
──────────────────
  MEMBROS ──────         ← Bölüm başlığı (label)
  ● Satış Asistanı       ← MembroAvatar + isim
  ● Destek Botu          ← Active: accent border sol çizgi
  ● Onboarding Uzmanı
  + Yeni Membro Ekle     ← CTA (ghost, icon)
──────────────────
  ⚙  Ayarlar             ← Alt kısım
  [Avatar] John Doe
──────────────────
```

**Membro listesi davranışı:**
- Kullanım frekansına göre sıralanır (AI personalization)
- Maksimum 7 item gösterilir, `+N daha` ile expand
- Hover'da tooltip (collapsed mod için isim)
- Click → `/membro/[guid]` hard navigation

### 3.3 Routing Şeması (Next.js App Router)

```
app/
├── (shell)/                    ← Layout shell (sidebar + topbar)
│   ├── layout.tsx
│   ├── dashboard/
│   │   └── page.tsx            → /dashboard
│   ├── membro/
│   │   ├── page.tsx            → /membro       (listeleme)
│   │   └── [guid]/
│   │       └── page.tsx        → /membro/[guid] (detay)
│   ├── meetings/
│   │   └── page.tsx            → /meetings      (Faz 4 entegrasyon)
│   └── knowledge/
│       └── page.tsx            → /knowledge     (ilerleyen fazlar)
├── (auth)/                     ← Auth akışı (shell yok)
│   ├── login/
│   │   └── page.tsx
│   └── ...
└── meeting/
    └── [roomId]/
        └── page.tsx            → /meeting/[roomId] (fullscreen, shell yok)
```

**Notlar:**
- `(shell)` route grubu: sidebar + topbar barındırır
- `/meeting/[roomId]`: fullscreen, shell hariç (Teams benzeri)
- Server Components default; sadece interaktif widget'lar `"use client"`

### 3.4 Component Pattern

**Atomic Design + Feature-based** hibrit:

```
src/
├── components/
│   ├── ui/                 ← Atom: Button, Badge, Avatar, Input, Skeleton
│   ├── layout/             ← Organism: Sidebar, TopBar, Shell
│   ├── membro/             ← Feature: MembroCard, MembroAvatar, MembroStatusBadge
│   ├── chat/               ← Feature: ChatBubble, ChatInput, ChatTimeline
│   ├── meeting/            ← Feature: MeetingParticipant, VoiceRoom (Faz 4)
│   └── modals/             ← Feature: CreateMembroModal, CreateMeetingModal
├── app/                    ← Next.js route pages
├── hooks/                  ← useMembroList, useChatStream, useMeeting
├── lib/                    ← API client, auth helpers
└── stores/                 ← Zustand: sidebar state, active membro
```

---

## 4. Sayfa Detayları

### 4.1 `/dashboard`

**Amaç:** Kullanıcının günlük başlangıç noktası. Hız ve bağlam.

#### Quick Actions Bar
- `+ Membro Yarat` → CreateMembro Modal tetikler
- `▶ Toplantı Başlat` → CreateMeeting Modal tetikler
- `🧠 Hafızayı Yönet` → `/knowledge` sayfasına yönlendirir
- Butonlar: `variant="outline-glow"`, accent renkli ikon, etrafında hafif glow

#### Aktif Membro Spotlight
Kullanıcının en sık kullandığı ya da en son etkileşime girdiği membro kartı büyük formatta gösterilir:
- İsim, persona özeti, son mesaj snippet'ı
- `Sohbete Devam Et` CTA → `/membro/[guid]`

#### Son Aktiviteler (Activity Feed)
- Gerçek zamanlı (ya da polling) son 10 etkinlik
- Tip: chat mesajı, toplantı kaydı, bilgi bankası güncellemesi
- Her item: zaman damgası + membro renk dot + kısa açıklama

#### Yaklaşan Toplantılar (opsiyonel, Faz 6.x)
- Bugün/bu hafta toplantıları kart formatında
- LiveKit room join CTA

#### AI Insight Card (2026 Pattern: Proactive Insights)
- LangGraph'tan üretilmiş tek cümlelik öneri (örn. "Satış Asistanın son 3 günde 12 soruya cevap verdi — bilgi bankasını güncellemeyi düşün")
- Dismissable, lokal storage'da saklanır

#### Layout: CSS Grid
```
[Quick Actions]                               (full width)
[Membro Spotlight]   [Activity Feed]          (60/40 split)
[Yaklaşan Toplantılar | AI Insight]           (50/50)
```

---

### 4.2 `/membro` — Listeleme

**Amaç:** Tüm membro'ları keşfet, yeni oluştur.

#### Header
- Sayfa başlığı: "Membro'larım"
- Sağ üst: `+ Membro Yarat` primary CTA → CreateMembro Modal

#### Grid Görünüm
- 3 kolon (masaüstü) / 2 kolon (tablet) / 1 kolon (mobil)
- `MembroCard` bileşeni (aşağıda detay)

#### Empty State
- Büyük, merkeze hizalı illüstrasyon (soyut ajan görseli)
- Başlık: "Henüz bir membro yok"
- Alt başlık: "İlk membro'nu oluşturarak başla"
- `+ Membro Yarat` CTA

#### MembroCard
```
┌─────────────────────────────────┐
│  [Avatar]  ● Aktif              │  ← Status badge
│  Satış Asistanı                 │  ← İsim
│  "Müşteri sorularını yönetir"   │  ← Kısa persona özeti
│                                 │
│  Son konuşma: 2 saat önce       │  ← Meta
│  [Sohbet Aç]  [···]             │  ← Actions
└─────────────────────────────────┘
```
- `bg-surface`, `border-default`, `radius-md`
- Hover: `border-active` + yukarı yükselme (translateY -2px, 80ms)
- onClick: `/membro/[guid]` navigasyonu
- `[···]` menu: Düzenle / Arşivle / Sil

#### Membro Avatarı
- İsmin baş harfleri + membro'ya atanmış renk (8 renk paletten)
- Büyük format (48px) detay sayfasında, küçük (32px) sidebar'da

---

### 4.3 CreateMembro Modal

**Tetikleyici:** Dashboard quick action, `/membro` sağ üst CTA

#### Layout: Full-Viewport Modal (%80)
```
┌─────────────────────────────────────────────────────────┐
│  [✕ Kapat]                                              │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │                  │  │                              │ │
│  │  MEMBRO LİSTESİ  │  │   SEÇİLİ MEMBRO ÖZELLİKLERİ │ │
│  │  (scrollable)    │  │                              │ │
│  │  ─────────────── │  │  İsim: _______________       │ │
│  │  ● Satış Ast.    │  │  Persona: ____________       │ │
│  │  ● Destek Botu   │  │  Sistem Prompt:              │ │
│  │  ● Onboarding    │  │  [textarea]                  │ │
│  │  ─────────────── │  │                              │ │
│  │                  │  │  Yetenekler (Tools):         │ │
│  │                  │  │  ☑ Bilgi Arama               │ │
│  │                  │  │  ☑ E-posta Gönder            │ │
│  │                  │  │  ☐ Takvim                    │ │
│  │                  │  │                              │ │
│  │                  │  │  [İptal]  [Kaydet →]         │ │
│  └──────────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Sol panel (30%):**
- Var olan membro'lar scrollable liste
- Her item: Avatar + isim + status chip
- Seçili item: accent sol border + hafif bg highlight

**Sağ panel (70%):**
- Seçili membro'nun form alanları
- `İsim` — text input
- `Persona Özeti` — kısa text input (maks 120 karakter)
- `Sistem Prompt` — multi-line textarea (LLM'e gidecek prompt)
- `Yetenekler (Tools / MCP Skills)` — checkbox listesi (backend'den çekilir)
- `[Kaydet]` → POST `/api/v1/membros/` veya PATCH (mevcut seçiliyse)

**Animasyon:** Sol + sağ panel ayrı `slide-in` ile girer. Modal backdrop: glass blur.

---

### 4.4 `/membro/[guid]` — Membro Detay

**Amaç:** Tek membro ile sohbet + aktivite geçmişi.

#### Layout: 3 Sütun
```
┌────────────────────────────────────────────────────────────┐
│ TopBar (global)                                            │
├──────────┬───────────────────────────┬─────────────────────┤
│          │                           │                     │
│ Sidebar  │   CHAT ALANI              │  AKTİVİTE PANELİ   │
│ (240px)  │   (esnek orta)            │  (320px, kaydırılabilir) │
│          │                           │                     │
└──────────┴───────────────────────────┴─────────────────────┘
```

**Chat Alanı (merkez, tam yükseklik):**

```
┌───────────────────────────────────────────────────┐
│  ● Satış Asistanı    [Toplantı Başlat] [···]      │  ← Membro header
│  "Müşteri sorularını yönetir"                     │
├───────────────────────────────────────────────────┤
│                                                   │
│      [Kullanıcı mesajı] ──────────────────▶       │
│                                                   │
│  ◀── [Membro yanıtı — streaming cursor]           │
│      [Tool çağrısı: knowledge_search] ...         │
│                                                   │
│      [Kullanıcı: ikinci mesaj] ────────────▶      │
│                                                   │
├───────────────────────────────────────────────────┤
│  [📎] [🎙 Ses]  Type a message...    [↑ Gönder]  │  ← Input bar
└───────────────────────────────────────────────────┘
```

**Chat özellikleri:**
- Streaming yanıt: SSE üzerinden karakter karakter render (WebSocket fallback)
- Tool çağrı göstergesi: "Bilgi bankasında arıyor..." collapsed chip
- Mesaj tipleştirme: `ChatBubble` bileşeni (user / assistant / tool-call / error)
- Kod blokları için syntax highlight (Shiki)
- Mesaj hover'ında: kopyala, beğen/beğenme, yeniden üret
- Scroll-to-bottom otomatik, sticky; yukarı scroll edince durdurulur

**Input Bar:**
- `Cmd+Enter` → gönder
- `📎` → dosya/url gönderimi (Faz 3 knowledge entegrasyon)
- `🎙 Ses` → Faz 4 realtime voice session başlatır
- Character limit göstergesi (max 4096)

**Aktivite Paneli (sağ, 320px):**

```
AKTİVİTELER ─────────────────
Bugün
  ─ 14:32  Bilgi araması yapıldı
            "Q3 raporu" sorguland..
  ─ 14:28  E-posta taslağı hazır
  ─ 14:10  Toplantı kaydı eklendi

Dün  
  ─ 09:15  Kullanıcı sohbeti (23 mesaj)

BİLGİ BANKASI ───────────────
  📄 Q3_rapor.pdf
  🌐 companysite.com/about
  + Kaynak Ekle
```

- Aktiviteler: backend `/api/v1/chat` geçmişi + webhook log (Faz 2)
- Bilgi bankası: `/api/v1/knowledge/docs` listesi (Faz 3)
- Tıklanabilir her item detay drawer açar

**Tablet/Mobil:** Aktivite paneli gizlenir, üstte toggle tab ile chat ↔ aktivite switch edilir.

---

### 4.5 CreateMeeting Modal

**Tetikleyici:** Dashboard, `/membro/[guid]` detay sayfası header butonu

#### Layout: Orta Boy Modal (480px genişlik)

```
┌──────────────────────────────────────┐
│  Yeni Toplantı                  [✕]  │
│                                      │
│  Membro Seç                          │
│  ┌──────────────────────────────┐    │
│  │ ▼ Satış Asistanı             │    │  ← select, detay sayfadan pre-fill
│  └──────────────────────────────┘    │
│                                      │
│  Toplantı Adı (opsiyonel)            │
│  ┌──────────────────────────────┐    │
│  │ Q3 Müşteri Görüşmesi         │    │
│  └──────────────────────────────┘    │
│                                      │
│  [İptal]            [Toplantıyı Başlat →]  │
└──────────────────────────────────────┘
```

**Davranış:**
- `/membro/[guid]` sayfasından açıldıysa → Membro Seç otomatik dolduruluyor (pre-filled, değiştirilebilir)
- Dashboard'dan açıldıysa → Membro dropdown boş
- `Toplantıyı Başlat` → `POST /api/v1/meetings/` → room_name döner → `/meeting/[roomId]` yönlendirme

---

### 4.6 `/meeting/[roomId]` — Toplantı Ekranı

**Amaç:** Gerçek zamanlı ses + membro ile sohbet. Teams benzeri.

**Shell DIŞINDA** — kendi `layout.tsx` var (fullscreen, no sidebar).

```
┌──────────────────────────────────────────────────────────┐
│  [← Çık]   Satış Asistanı Toplantısı   [REC ●]  [00:14]  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │                                                    │  │
│  │              [Membro Avatar — büyük]               │  │
│  │           ████████████ (ses dalgası animasyon)     │  │
│  │              "Satış Asistanı"                      │  │
│  │                                                    │  │
│  ├────────────────────────────────────────────────────┤  │
│  │  Live transcript:                                  │  │
│  │  "Merhaba, size nasıl yardımcı olabilirim?"        │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│        [🎙 Mikrofon] [📷 Kamera] [✋ El Kaldır] [✕ Kapat]│
└──────────────────────────────────────────────────────────┘
```

**Bileşenler:**
- `VoiceRoom` (Faz 4'ten var) — LiveKit React SDK
- Membro avatar + ses dalga animasyonu (VAD aktifken pulse)
- Live transcript overlay — `MeetingTranscript` bileşeni
- Kontrol bar: `ControlBar` (mute, leave, el kaldır)
- Toplantı bitişinde: özet modal → transcript PDF download + `/membro/[guid]`'e dön

> **Not:** Birden fazla membro katılımcı desteklenecekse (ilerleyen sürümler), Microsoft Teams'deki gibi grid layout kullanılır. Şimdilik tek membro → tek büyük kart.

---

## 5. Genel Component Kataloğu

| Bileşen | Konum | Açıklama |
|---|---|---|
| `Button` | `ui/` | `primary`, `outline`, `ghost`, `danger` + `size` prop |
| `Badge` / `StatusBadge` | `ui/` | Renk + label, membro durumu |
| `Avatar` | `ui/` | İnitials + renk, opsiyonel image |
| `Skeleton` | `ui/` | Loading placeholder, her kart için |
| `Modal` | `ui/` | Base modal, AnimatePresence wrapper |
| `Spinner` | `ui/` | AI yanıt bekleme, upload |
| `Sidebar` | `layout/` | Collapse/expand, membro listesi |
| `TopBar` | `layout/` | Logo, bildirimler, avatar menu |
| `MembroCard` | `membro/` | Listeleme kartı |
| `MembroAvatar` | `membro/` | Renkli initials avatar |
| `ChatBubble` | `chat/` | user / assistant / tool-call varyantları |
| `ChatInput` | `chat/` | Textarea, gönder butonu, voice trigger |
| `ChatTimeline` | `chat/` | Mesaj listesi, scroll management, streaming |
| `ActivityFeed` | `dashboard/` | Event listesi, zaman damgası |
| `QuickActionBar` | `dashboard/` | İkon + label CTA butonları |
| `CreateMembroModal` | `modals/` | Split-panel, membro form |
| `CreateMeetingModal` | `modals/` | Compact, membro seç + başlat |
| `VoiceRoom` | `meeting/` | LiveKit wrapper (Faz 4'ten migrate) |

---

## 6. State Yönetimi

**Zustand** (lightweight, SSR uyumlu):

```typescript
// stores/appStore.ts
interface AppStore {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  activeMembro: Membro | null;
  setActiveMembro: (m: Membro | null) => void;

  createMembroModalOpen: boolean;
  createMeetingModalOpen: boolean;
  openCreateMembro: () => void;
  openCreateMeeting: (prefilledMembroId?: string) => void;
  closeModals: () => void;
}
```

**TanStack Query** (server state, caching):
- `useMembroList()` → GET `/api/v1/membros/`
- `useMembro(guid)` → GET `/api/v1/membros/[guid]`
- `useChatHistory(membroId)` → GET `/api/v1/chat/?membro_id=...`
- `useActivityFeed()` → polling her 30 saniyede
- `useKnowledgeDocs(membroId)` → GET `/api/v1/knowledge/docs`

---

## 7. API Entegrasyon Haritası

| Sayfa / Bileşen | Backend Endpoint | Yöntem |
|---|---|---|
| Sidebar membro listesi | `GET /api/v1/membros/` | TanStack Query |
| Membro kartı | `GET /api/v1/membros/{id}` | Server Component fetch |
| Membro yarat/güncelle | `POST / PATCH /api/v1/membros/` | React Query mutation |
| Chat | `POST /api/v1/chat/` | fetch + ReadableStream (SSE) |
| Chat geçmişi | `GET /api/v1/chat/?membro_id=` | TanStack Query |
| Toplantı başlat | `POST /api/v1/meetings/` | mutation → redirect |
| LiveKit token | (mevcut meeting endpoint'inden) | Faz 4 API |
| Bilgi bankası listesi | `GET /api/v1/knowledge/docs` | TanStack Query |
| Bilgi bankası ekle | `POST /api/v1/knowledge/docs` | mutation |

---

## 8. Accessibility (a11y)

- WCAG 2.1 AA minimum
- Tüm interaktif elementler `focus-visible` ring (accent renk)
- `aria-label` her ikon buton için zorunlu
- Keyboard navigation: `Tab` akışı doğal, modal `focus-trap`
- Color contrast: `text-primary` üzerinde AA geçer (4.5:1+)
- `prefers-reduced-motion`: animasyonlar `duration: 0ms`'e düşer
- Screen reader: chat mesajları `role="log" aria-live="polite"`

---

## 9. Performans Hedefleri

| Metrik | Hedef |
|---|---|
| LCP (Largest Contentful Paint) | < 1.5s |
| FID / INP | < 100ms |
| CLS | < 0.05 |
| First chat message render | < 800ms |
| Sidebar open/close | < 120ms |
| Modal open | < 100ms |

**Stratejiler:**
- Server Components ile initial HTML prefill (membro listesi, dashboard data)
- Route segment'leri için `loading.tsx` skeleton
- `next/image` ile avatar ve görseller optimize
- Tailwind JIT — sadece kullanılan CSS bundle'a girer
- `React.lazy` + `Suspense` ile modal bileşenleri lazy-load

---

## 10. Faz 6 Alt Görevler (Milestones)

### Faz 6.0 — Temel Altyapı
- [ ] Design token'ları Tailwind config'e aktar (`tailwind.config.ts`)
- [ ] `ui/` atom bileşenleri: Button, Badge, Avatar, Skeleton, Modal, Spinner
- [ ] Zustand store kurulumu
- [ ] TanStack Query provider + API client (JWT header inject)
- [ ] `(shell)` layout: Sidebar + TopBar + içerik alanı
- [ ] Sidebar: nav, membro listesi, collapse

### Faz 6.1 — Dashboard
- [ ] Quick Action Bar
- [ ] Membro Spotlight card
- [ ] Activity Feed (polling)
- [ ] AI Insight Card
- [ ] `/dashboard` page iskelet + responsive grid

### Faz 6.2 — Membro Listeleme & Kart
- [ ] `MembroCard` bileşeni
- [ ] `/membro` sayfa grid layout
- [ ] Empty state bileşeni
- [ ] Membro listesi API bağlantısı

### Faz 6.3 — CreateMembro Modal
- [ ] Modal base (glass backdrop, AnimatePresence)
- [ ] Sol panel: scrollable membro listesi
- [ ] Sağ panel: form (isim, persona, sistem prompt, tool seçimi)
- [ ] POST / PATCH API entegrasyon + optimistic update

### Faz 6.4 — Membro Detay & Chat
- [ ] 3-sütun layout
- [ ] `ChatTimeline` + `ChatBubble` bileşenleri
- [ ] `ChatInput` (streaming, keyboard shortcuts)
- [ ] SSE / ReadableStream API bağlantısı (Faz 2 chat endpoint)
- [ ] Tool call gösterge chip'i
- [ ] Aktivite paneli (geçmiş, bilgi bankası)

### Faz 6.5 — CreateMeeting Modal & Meeting Sayfası
- [ ] `CreateMeetingModal` bileşeni (membro pre-fill desteği)
- [ ] `/meeting/[roomId]` fullscreen layout
- [ ] `VoiceRoom` Faz 4'ten migrate + ses dalga animasyon
- [ ] Live transcript overlay
- [ ] Toplantı bitiş modal (özet, dön CTA)

### Faz 6.x — İlerleyen Görevler (Kapsam Dışı, Şimdilik)
- [ ] `/knowledge` — Bilgi bankası yönetimi UI
- [ ] Membro düzenleme sayfası (`/membro/[guid]/edit`)
- [ ] Auth kullanıcı profili düzenleme
- [ ] Tenant ayarları sayfası
- [ ] Bildirim sistemi (TopBar bell icon)
- [ ] Dark/Light mode toggle
- [ ] `/meetings` geçmiş listesi
- [ ] Onboarding flow (ilk kez giriş yapan tenant)

---

## 11. Bağımlılıklar (package.json eklentileri)

```json
{
  "dependencies": {
    "next": "^16.1.0",
    "react": "^19.0.0",
    "typescript": "^5.x",
    "tailwindcss": "^4.x",
    "@tanstack/react-query": "^5.x",
    "zustand": "^5.x",
    "framer-motion": "^11.x",
    "shiki": "^1.x",
    "@livekit/components-react": "^2.x",
    "livekit-client": "^2.x",
    "lucide-react": "^0.4x"
  }
}
```

> `shadcn/ui` önce **kullanılmaz** — design token'ları kendi sistemdir. Gerektiğinde `shadcn` bileşenleri token'larla override edilerek entegre edilebilir.

---

## 12. Kararlar ve Gerekçeler

| Karar | Gerekçe |
|---|---|
| Framer Motion animasyonlar | Spring-based modal, 2026 liquid glass estetiği için daha doğal his |
| Tailwind v4 + CSS custom properties | Design token sistemi doğrudan CSS var olarak çalışır |
| Server Components ilk tercih | LCP optimize, membro liste initial render hızlı |
| TanStack Query | Stale-while-revalidate + optimistic update = chat gibi gerçek zamanlı değişimler |
| SSE (Server-Sent Events) chat stream | WebSocket'ten daha basit, FastAPI native SSE ile uyumlu |
| Zustand UI state | Redux'tan daha hafif; modal, sidebar gibi UI-only state için yeterli |
| Kendi design token sistemi | shadcn/ui bileşenlerinin kırılganlığından kaçınmak, tam kontrol |
