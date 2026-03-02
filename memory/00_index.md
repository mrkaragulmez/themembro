# Memory Index

Bu klasör, Membro projesi boyunca GitHub Copilot ile sürdürülen çalışma hafızasını yönetir.
Her konuşma başında ve sonunda bu dosyalar okunup güncellenerek kesintisiz bağlam sağlanır.

## Dosyalar

| Dosya | İçerik |
|---|---|
| `00_index.md` | Bu dosya. Hafıza sisteminin haritası. |
| `01_project_state.md` | Fazların mevcut durumu, tamamlanan ve bekleyen görevler. |
| `02_decisions.md` | Alınan mimari ve teknik kararların kalıcı logu. |
| `03_active_context.md` | Şu an üzerinde çalışılan konu, açık sorular, sonraki adım. |

## Kullanım Kuralları

1. **Oturum başında**: `00_index.md` → `01_project_state.md` → `03_active_context.md` sırasıyla oku.
2. **Görev tamamlandığında**: `01_project_state.md` güncelle.
3. **Karar alındığında**: `02_decisions.md`'ye yeni bir kayıt ekle.
4. **Oturum sonunda veya konu değiştiğinde**: `03_active_context.md` güncelle.
