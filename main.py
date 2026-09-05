# -*- coding: utf-8 -*-
"""
main.py
Adisyon Sistemi - Ana Uygulama (Tkinter)

Çalıştırmak için: python main.py
.exe yapmak için: build.bat dosyasına bakınız.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime

from database import Database

# ----------------------------------------------------------------------
# Renkler / Stil
# ----------------------------------------------------------------------
RENK_BG = "#1e2530"
RENK_PANEL = "#2a3341"
RENK_VURGU = "#3d7fff"
RENK_YESIL = "#2ecc71"
RENK_KIRMIZI = "#e74c3c"
RENK_METIN = "#e8eaed"
RENK_METIN_SOFT = "#9aa4b2"
RENK_MASA_BOS = "#2ecc71"
RENK_MASA_DOLU = "#e74c3c"

FONT_BASLIK = ("Segoe UI", 18, "bold")
FONT_NORMAL = ("Segoe UI", 11)
FONT_KUCUK = ("Segoe UI", 9)
FONT_BUTON = ("Segoe UI", 11, "bold")


class AdisyonUygulamasi(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Adisyon Sistemi")
        self.geometry("1150x700")
        self.minsize(1000, 620)
        self.configure(bg=RENK_BG)

        self.db = Database()

        self._stil_ayarla()
        self._ana_yerlesim()
        self.masalar_ekranini_goster()

        self.protocol("WM_DELETE_WINDOW", self._kapanirken)

    # ------------------------------------------------------------------
    def _stil_ayarla(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", background="#232b38", fieldbackground="#232b38",
                         foreground=RENK_METIN, rowheight=28, font=FONT_NORMAL, borderwidth=0)
        style.configure("Treeview.Heading", background=RENK_PANEL, foreground=RENK_METIN,
                         font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", RENK_VURGU)])

    def _ana_yerlesim(self):
        # Üst menü çubuğu
        self.ust_bar = tk.Frame(self, bg=RENK_PANEL, height=54)
        self.ust_bar.pack(side="top", fill="x")
        self.ust_bar.pack_propagate(False)

        tk.Label(self.ust_bar, text="🧾 Adisyon Sistemi", bg=RENK_PANEL, fg=RENK_METIN,
                 font=FONT_BASLIK).pack(side="left", padx=20)

        buton_stili = dict(bg=RENK_PANEL, fg=RENK_METIN, font=FONT_NORMAL, bd=0,
                            activebackground=RENK_VURGU, activeforeground="white",
                            cursor="hand2", padx=14, pady=8)

        tk.Button(self.ust_bar, text="🍽 Masalar", command=self.masalar_ekranini_goster,
                   **buton_stili).pack(side="left", padx=4)
        tk.Button(self.ust_bar, text="📋 Ürün/Menü Yönetimi", command=self.urun_yonetimi_goster,
                   **buton_stili).pack(side="left", padx=4)
        tk.Button(self.ust_bar, text="📊 Satış Raporu", command=self.rapor_goster,
                   **buton_stili).pack(side="left", padx=4)

        self.saat_label = tk.Label(self.ust_bar, text="", bg=RENK_PANEL, fg=RENK_METIN_SOFT,
                                    font=FONT_KUCUK)
        self.saat_label.pack(side="right", padx=20)
        self._saati_guncelle()

        # İçerik alanı
        self.icerik = tk.Frame(self, bg=RENK_BG)
        self.icerik.pack(side="top", fill="both", expand=True)

    def _saati_guncelle(self):
        simdi = datetime.datetime.now().strftime("%d.%m.%Y  %H:%M:%S")
        self.saat_label.config(text=simdi)
        self.after(1000, self._saati_guncelle)

    def _icerik_temizle(self):
        for w in self.icerik.winfo_children():
            w.destroy()

    def _kapanirken(self):
        self.db.close()
        self.destroy()

    # ==================================================================
    # MASALAR EKRANI
    # ==================================================================
    def masalar_ekranini_goster(self):
        self._icerik_temizle()
        container = tk.Frame(self.icerik, bg=RENK_BG)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        ust = tk.Frame(container, bg=RENK_BG)
        ust.pack(fill="x", pady=(0, 15))
        tk.Label(ust, text="Masalar", bg=RENK_BG, fg=RENK_METIN,
                 font=("Segoe UI", 15, "bold")).pack(side="left")
        tk.Button(ust, text="+ Masa Ekle", bg=RENK_VURGU, fg="white", font=FONT_NORMAL,
                   bd=0, padx=12, pady=6, cursor="hand2",
                   command=self._masa_ekle_dialog).pack(side="right")

        # Kaydırılabilir grid alanı
        canvas = tk.Canvas(container, bg=RENK_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        grid_frame = tk.Frame(canvas, bg=RENK_BG)

        grid_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=grid_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        masalar = self.db.masalari_getir()
        kolon_sayisi = 5
        for idx, masa in enumerate(masalar):
            satir, sutun = divmod(idx, kolon_sayisi)
            self._masa_karti_olustur(grid_frame, masa, satir, sutun)

    def _masa_karti_olustur(self, parent, masa, satir, sutun):
        renk = RENK_MASA_BOS if masa["durum"] == "bos" else RENK_MASA_DOLU
        toplam_str = ""
        if masa["durum"] == "dolu":
            siparis = self.db.acik_siparis_getir(masa["id"])
            if siparis:
                toplam = self.db.siparis_toplam(siparis["id"])
                toplam_str = f"{toplam:.2f} TL"

        kart = tk.Frame(parent, bg=RENK_PANEL, width=180, height=120,
                         highlightbackground=renk, highlightthickness=3)
        kart.grid(row=satir, column=sutun, padx=10, pady=10)
        kart.pack_propagate(False)
        kart.grid_propagate(False)

        tk.Label(kart, text=masa["isim"], bg=RENK_PANEL, fg=RENK_METIN,
                 font=("Segoe UI", 13, "bold")).pack(pady=(16, 4))
        durum_metin = "Boş" if masa["durum"] == "bos" else "Dolu"
        tk.Label(kart, text=durum_metin, bg=RENK_PANEL, fg=renk,
                 font=FONT_KUCUK).pack()
        if toplam_str:
            tk.Label(kart, text=toplam_str, bg=RENK_PANEL, fg=RENK_METIN_SOFT,
                     font=FONT_KUCUK).pack(pady=(4, 0))

        for w in (kart,) + tuple(kart.winfo_children()):
            w.bind("<Button-1>", lambda e, m=masa: self.siparis_ekranini_ac(m))
            w.bind("<Button-3>", lambda e, m=masa: self._masa_sag_tik_menu(e, m))
        kart.config(cursor="hand2")

    def _masa_sag_tik_menu(self, event, masa):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Masayı Sil", command=lambda: self._masa_sil(masa))
        menu.tk_popup(event.x_root, event.y_root)

    def _masa_sil(self, masa):
        if masa["durum"] == "dolu":
            messagebox.showwarning("Uyarı", "Dolu bir masa silinemez. Önce hesabı kapatın.")
            return
        if messagebox.askyesno("Onay", f"{masa['isim']} silinsin mi?"):
            self.db.masa_sil(masa["id"])
            self.masalar_ekranini_goster()

    def _masa_ekle_dialog(self):
        isim = simpledialog.askstring("Yeni Masa", "Masa adı:", parent=self)
        if isim:
            self.db.masa_ekle(isim.strip())
            self.masalar_ekranini_goster()

    # ==================================================================
    # SİPARİŞ / ADİSYON EKRANI
    # ==================================================================
    def siparis_ekranini_ac(self, masa):
        siparis = self.db.acik_siparis_getir(masa["id"])
        if not siparis:
            siparis_id = self.db.siparis_ac(masa["id"])
        else:
            siparis_id = siparis["id"]

        self._icerik_temizle()
        container = tk.Frame(self.icerik, bg=RENK_BG)
        container.pack(fill="both", expand=True, padx=20, pady=15)

        # Üst bar
        ust = tk.Frame(container, bg=RENK_BG)
        ust.pack(fill="x", pady=(0, 10))
        tk.Button(ust, text="← Masalara Dön", bg=RENK_PANEL, fg=RENK_METIN, bd=0,
                   font=FONT_NORMAL, padx=10, pady=6, cursor="hand2",
                   command=self.masalar_ekranini_goster).pack(side="left")
        tk.Label(ust, text=f"  {masa['isim']} - Adisyon", bg=RENK_BG, fg=RENK_METIN,
                 font=("Segoe UI", 15, "bold")).pack(side="left", padx=10)

        gövde = tk.Frame(container, bg=RENK_BG)
        gövde.pack(fill="both", expand=True)

        # SOL: Menü / ürün seçimi
        sol = tk.Frame(gövde, bg=RENK_PANEL)
        sol.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(sol, text="Menü", bg=RENK_PANEL, fg=RENK_METIN,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 6))

        kategoriler = self.db.kategorileri_getir()
        kat_secim = tk.StringVar(value="Tümü")
        kat_frame = tk.Frame(sol, bg=RENK_PANEL)
        kat_frame.pack(fill="x", padx=10)

        urun_liste_frame = tk.Frame(sol, bg=RENK_PANEL)
        urun_liste_frame.pack(fill="both", expand=True, padx=10, pady=10)

        def urunleri_yukle(kategori_id=None):
            for w in urun_liste_frame.winfo_children():
                w.destroy()
            canvas = tk.Canvas(urun_liste_frame, bg=RENK_PANEL, highlightthickness=0)
            sb = ttk.Scrollbar(urun_liste_frame, orient="vertical", command=canvas.yview)
            iç = tk.Frame(canvas, bg=RENK_PANEL)
            iç.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=iç, anchor="nw", width=360)
            canvas.configure(yscrollcommand=sb.set)
            canvas.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")

            urunler = self.db.urunleri_getir(kategori_id)
            for u in urunler:
                satir = tk.Frame(iç, bg="#232b38")
                satir.pack(fill="x", pady=3, padx=2)
                tk.Label(satir, text=u["isim"], bg="#232b38", fg=RENK_METIN,
                         font=FONT_NORMAL, width=22, anchor="w").pack(side="left", padx=8, pady=8)
                tk.Label(satir, text=f"{u['fiyat']:.2f} TL", bg="#232b38", fg=RENK_METIN_SOFT,
                         font=FONT_KUCUK, width=10).pack(side="left")
                tk.Button(satir, text="Ekle +", bg=RENK_VURGU, fg="white", bd=0,
                           font=FONT_KUCUK, padx=10, pady=4, cursor="hand2",
                           command=lambda urun=u: urun_ekle(urun)).pack(side="right", padx=8)

        def kategori_sec(kat_id, buton_metin):
            kat_secim.set(buton_metin)
            urunleri_yukle(kat_id)

        tk.Button(kat_frame, text="Tümü", bg=RENK_VURGU, fg="white", bd=0, font=FONT_KUCUK,
                   padx=10, pady=5, cursor="hand2",
                   command=lambda: kategori_sec(None, "Tümü")).pack(side="left", padx=3, pady=3)
        for k in kategoriler:
            tk.Button(kat_frame, text=k["isim"], bg=RENK_BG, fg=RENK_METIN, bd=0, font=FONT_KUCUK,
                       padx=10, pady=5, cursor="hand2",
                       command=lambda kid=k["id"], nm=k["isim"]: kategori_sec(kid, nm)
                       ).pack(side="left", padx=3, pady=3)

        # SAĞ: Sepet / adisyon detayı
        sag = tk.Frame(gövde, bg=RENK_PANEL, width=380)
        sag.pack(side="right", fill="y")
        sag.pack_propagate(False)

        tk.Label(sag, text="Sipariş Detayı", bg=RENK_PANEL, fg=RENK_METIN,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(12, 6))

        columns = ("urun", "adet", "tutar")
        tree = ttk.Treeview(sag, columns=columns, show="headings", height=14)
        tree.heading("urun", text="Ürün")
        tree.heading("adet", text="Adet")
        tree.heading("tutar", text="Tutar")
        tree.column("urun", width=170)
        tree.column("adet", width=60, anchor="center")
        tree.column("tutar", width=90, anchor="e")
        tree.pack(fill="both", expand=True, padx=10)

        toplam_label = tk.Label(sag, text="Toplam: 0.00 TL", bg=RENK_PANEL, fg=RENK_YESIL,
                                 font=("Segoe UI", 14, "bold"))
        toplam_label.pack(pady=10)

        detay_map = {}  # tree item id -> detay id

        def sepeti_yenile():
            for i in tree.get_children():
                tree.delete(i)
            detaylar = self.db.siparis_detaylari(siparis_id)
            for d in detaylar:
                tutar = d["birim_fiyat"] * d["adet"]
                iid = tree.insert("", "end", values=(d["urun_isim"], d["adet"], f"{tutar:.2f}"))
                detay_map[iid] = d["id"]
            toplam = self.db.siparis_toplam(siparis_id)
            toplam_label.config(text=f"Toplam: {toplam:.2f} TL")

        def urun_ekle(urun):
            self.db.urun_ekle_siparise(siparis_id, urun["id"], urun["isim"], urun["fiyat"], 1)
            sepeti_yenile()

        def secili_adet_degistir(delta):
            sec = tree.selection()
            if not sec:
                return
            detay_id = detay_map.get(sec[0])
            if detay_id is None:
                return
            detaylar = self.db.siparis_detaylari(siparis_id)
            mevcut = next((d for d in detaylar if d["id"] == detay_id), None)
            if mevcut:
                self.db.detay_adet_guncelle(detay_id, mevcut["adet"] + delta)
                sepeti_yenile()

        def secili_sil():
            sec = tree.selection()
            if not sec:
                return
            detay_id = detay_map.get(sec[0])
            if detay_id is not None:
                self.db.detay_sil(detay_id)
                sepeti_yenile()

        buton_satir = tk.Frame(sag, bg=RENK_PANEL)
        buton_satir.pack(pady=(0, 8))
        tk.Button(buton_satir, text="－", bg=RENK_BG, fg=RENK_METIN, bd=0, font=FONT_BUTON,
                   width=3, cursor="hand2", command=lambda: secili_adet_degistir(-1)).pack(side="left", padx=3)
        tk.Button(buton_satir, text="＋", bg=RENK_BG, fg=RENK_METIN, bd=0, font=FONT_BUTON,
                   width=3, cursor="hand2", command=lambda: secili_adet_degistir(1)).pack(side="left", padx=3)
        tk.Button(buton_satir, text="Sil", bg=RENK_KIRMIZI, fg="white", bd=0, font=FONT_KUCUK,
                   padx=10, cursor="hand2", command=secili_sil).pack(side="left", padx=3)

        alt_buton_satir = tk.Frame(sag, bg=RENK_PANEL)
        alt_buton_satir.pack(fill="x", padx=10, pady=(4, 14), side="bottom")

        tk.Button(alt_buton_satir, text="İptal Et (Boşalt)", bg=RENK_BG, fg=RENK_METIN_SOFT, bd=0,
                   font=FONT_KUCUK, padx=10, pady=8, cursor="hand2",
                   command=lambda: self._siparis_iptal(masa)).pack(fill="x", pady=(0, 6))
        tk.Button(alt_buton_satir, text="✓ Hesabı Kapat / Adisyon Yazdır", bg=RENK_YESIL, fg="white",
                   bd=0, font=FONT_BUTON, padx=10, pady=10, cursor="hand2",
                   command=lambda: self._hesap_kapat(masa)).pack(fill="x")

        urunleri_yukle(None)
        sepeti_yenile()

    def _siparis_iptal(self, masa):
        if messagebox.askyesno("Onay", "Sipariş iptal edilip masa boşaltılsın mı?\n(Hesap alınmayacak)"):
            self.db.siparisi_iptal_et(masa["id"])
            self.masalar_ekranini_goster()

    def _hesap_kapat(self, masa):
        siparis = self.db.acik_siparis_getir(masa["id"])
        if not siparis:
            return
        detaylar = self.db.siparis_detaylari(siparis["id"])
        if not detaylar:
            messagebox.showwarning("Uyarı", "Siparişte ürün yok.")
            return

        odeme_tipi = self._odeme_tipi_sec()
        if odeme_tipi is None:
            return

        sonuc = self.db.hesabi_kapat(masa["id"], odeme_tipi)
        self._adisyon_fisi_goster(sonuc, odeme_tipi)
        self.masalar_ekranini_goster()

    def _odeme_tipi_sec(self):
        pencere = tk.Toplevel(self)
        pencere.title("Ödeme Tipi")
        pencere.configure(bg=RENK_PANEL)
        pencere.geometry("300x160")
        pencere.transient(self)
        pencere.grab_set()

        secim = {"deger": None}
        tk.Label(pencere, text="Ödeme tipi seçin:", bg=RENK_PANEL, fg=RENK_METIN,
                 font=FONT_NORMAL).pack(pady=(20, 10))

        def sec(v):
            secim["deger"] = v
            pencere.destroy()

        for tip in ("Nakit", "Kredi Kartı", "Yemek Kartı"):
            tk.Button(pencere, text=tip, bg=RENK_VURGU, fg="white", bd=0, font=FONT_NORMAL,
                       pady=8, cursor="hand2", command=lambda v=tip: sec(v)).pack(fill="x", padx=20, pady=4)

        self.wait_window(pencere)
        return secim["deger"]

    def _adisyon_fisi_goster(self, sonuc, odeme_tipi):
        pencere = tk.Toplevel(self)
        pencere.title("Adisyon Fişi")
        pencere.configure(bg="white")
        pencere.geometry("360x520")

        metin = tk.Text(pencere, bg="white", fg="black", font=("Consolas", 11), bd=0)
        metin.pack(fill="both", expand=True, padx=10, pady=10)

        fis = []
        fis.append("=" * 34)
        fis.append("           ADİSYON FİŞİ")
        fis.append("=" * 34)
        fis.append(f"Masa   : {sonuc['masa_isim']}")
        fis.append(f"Tarih  : {sonuc['tarih'].replace('T', ' ')}")
        fis.append(f"Ödeme  : {odeme_tipi}")
        fis.append("-" * 34)
        for d in sonuc["detaylar"]:
            ad = d["urun_isim"]
            adet = d["adet"]
            tutar = d["birim_fiyat"] * d["adet"]
            fis.append(f"{ad:<18} x{adet:<3} {tutar:>8.2f} TL")
        fis.append("-" * 34)
        fis.append(f"{'TOPLAM':<22}{sonuc['toplam']:>10.2f} TL")
        fis.append("=" * 34)
        fis.append("        Bizi tercih ettiğiniz için")
        fis.append("              teşekkürler!")

        metin.insert("1.0", "\n".join(fis))
        metin.config(state="disabled")

        tk.Button(pencere, text="Kapat", bg=RENK_VURGU, fg="white", bd=0, font=FONT_NORMAL,
                   pady=8, cursor="hand2", command=pencere.destroy).pack(fill="x", padx=10, pady=(0, 10))

    # ==================================================================
    # ÜRÜN / MENÜ YÖNETİMİ
    # ==================================================================
    def urun_yonetimi_goster(self):
        self._icerik_temizle()
        container = tk.Frame(self.icerik, bg=RENK_BG)
        container.pack(fill="both", expand=True, padx=20, pady=15)

        ust = tk.Frame(container, bg=RENK_BG)
        ust.pack(fill="x", pady=(0, 10))
        tk.Label(ust, text="Ürün / Menü Yönetimi", bg=RENK_BG, fg=RENK_METIN,
                 font=("Segoe UI", 15, "bold")).pack(side="left")
        tk.Button(ust, text="+ Kategori Ekle", bg=RENK_PANEL, fg=RENK_METIN, bd=0,
                   font=FONT_NORMAL, padx=12, pady=6, cursor="hand2",
                   command=self._kategori_ekle_dialog).pack(side="right", padx=4)
        tk.Button(ust, text="+ Ürün Ekle", bg=RENK_VURGU, fg="white", bd=0,
                   font=FONT_NORMAL, padx=12, pady=6, cursor="hand2",
                   command=self._urun_ekle_dialog).pack(side="right", padx=4)

        columns = ("isim", "kategori", "fiyat")
        tree = ttk.Treeview(container, columns=columns, show="headings", height=20)
        tree.heading("isim", text="Ürün Adı")
        tree.heading("kategori", text="Kategori")
        tree.heading("fiyat", text="Fiyat (TL)")
        tree.column("isim", width=280)
        tree.column("kategori", width=180)
        tree.column("fiyat", width=120, anchor="e")
        tree.pack(fill="both", expand=True, pady=10)

        urun_map = {}
        for u in self.db.urunleri_getir():
            iid = tree.insert("", "end", values=(u["isim"], u["kategori_isim"] or "-", f"{u['fiyat']:.2f}"))
            urun_map[iid] = u["id"]

        alt = tk.Frame(container, bg=RENK_BG)
        alt.pack(fill="x")

        def secili_duzenle():
            sec = tree.selection()
            if not sec:
                return
            self._urun_duzenle_dialog(urun_map[sec[0]])

        def secili_sil():
            sec = tree.selection()
            if not sec:
                return
            if messagebox.askyesno("Onay", "Ürün silinsin mi?"):
                self.db.urun_sil(urun_map[sec[0]])
                self.urun_yonetimi_goster()

        tk.Button(alt, text="Düzenle", bg=RENK_PANEL, fg=RENK_METIN, bd=0, font=FONT_NORMAL,
                   padx=14, pady=8, cursor="hand2", command=secili_duzenle).pack(side="left", padx=4, pady=6)
        tk.Button(alt, text="Sil", bg=RENK_KIRMIZI, fg="white", bd=0, font=FONT_NORMAL,
                   padx=14, pady=8, cursor="hand2", command=secili_sil).pack(side="left", padx=4)

    def _kategori_ekle_dialog(self):
        isim = simpledialog.askstring("Yeni Kategori", "Kategori adı:", parent=self)
        if isim:
            self.db.kategori_ekle(isim.strip())
            self.urun_yonetimi_goster()

    def _urun_form_penceresi(self, baslik, urun=None):
        pencere = tk.Toplevel(self)
        pencere.title(baslik)
        pencere.configure(bg=RENK_PANEL)
        pencere.geometry("340x300")
        pencere.transient(self)
        pencere.grab_set()

        tk.Label(pencere, text="Ürün Adı", bg=RENK_PANEL, fg=RENK_METIN, font=FONT_NORMAL).pack(pady=(16, 4))
        isim_entry = tk.Entry(pencere, font=FONT_NORMAL)
        isim_entry.pack(fill="x", padx=20)

        tk.Label(pencere, text="Fiyat (TL)", bg=RENK_PANEL, fg=RENK_METIN, font=FONT_NORMAL).pack(pady=(14, 4))
        fiyat_entry = tk.Entry(pencere, font=FONT_NORMAL)
        fiyat_entry.pack(fill="x", padx=20)

        tk.Label(pencere, text="Kategori", bg=RENK_PANEL, fg=RENK_METIN, font=FONT_NORMAL).pack(pady=(14, 4))
        kategoriler = self.db.kategorileri_getir()
        kat_isimleri = [k["isim"] for k in kategoriler]
        kat_id_map = {k["isim"]: k["id"] for k in kategoriler}
        kat_var = tk.StringVar()
        kat_combo = ttk.Combobox(pencere, textvariable=kat_var, values=kat_isimleri, state="readonly")
        kat_combo.pack(fill="x", padx=20)

        if urun:
            isim_entry.insert(0, urun["isim"])
            fiyat_entry.insert(0, str(urun["fiyat"]))
            if urun["kategori_isim"]:
                kat_var.set(urun["kategori_isim"])
        elif kat_isimleri:
            kat_var.set(kat_isimleri[0])

        def kaydet():
            isim = isim_entry.get().strip()
            fiyat_str = fiyat_entry.get().strip().replace(",", ".")
            kat_isim = kat_var.get()
            if not isim or not fiyat_str or not kat_isim:
                messagebox.showwarning("Uyarı", "Tüm alanları doldurun.")
                return
            try:
                fiyat = float(fiyat_str)
            except ValueError:
                messagebox.showwarning("Uyarı", "Fiyat sayısal olmalı.")
                return
            kat_id = kat_id_map[kat_isim]
            if urun:
                self.db.urun_guncelle(urun["id"], isim, fiyat, kat_id)
            else:
                self.db.urun_ekle(isim, fiyat, kat_id)
            pencere.destroy()
            self.urun_yonetimi_goster()

        tk.Button(pencere, text="Kaydet", bg=RENK_VURGU, fg="white", bd=0, font=FONT_BUTON,
                   pady=8, cursor="hand2", command=kaydet).pack(fill="x", padx=20, pady=20)

    def _urun_ekle_dialog(self):
        self._urun_form_penceresi("Yeni Ürün")

    def _urun_duzenle_dialog(self, urun_id):
        urunler = self.db.urunleri_getir(sadece_aktif=False)
        urun = next((u for u in urunler if u["id"] == urun_id), None)
        if urun:
            self._urun_form_penceresi("Ürünü Düzenle", urun)

    # ==================================================================
    # SATIŞ RAPORU
    # ==================================================================
    def rapor_goster(self):
        self._icerik_temizle()
        container = tk.Frame(self.icerik, bg=RENK_BG)
        container.pack(fill="both", expand=True, padx=20, pady=15)

        tk.Label(container, text="Satış Raporu", bg=RENK_BG, fg=RENK_METIN,
                 font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 10))

        gunluk, gunluk_toplam = self.db.gunluk_satis()
        ozet = tk.Frame(container, bg=RENK_PANEL)
        ozet.pack(fill="x", pady=(0, 14))
        tk.Label(ozet, text=f"Bugünkü Satış: {gunluk_toplam:.2f} TL   ({len(gunluk)} adisyon)",
                 bg=RENK_PANEL, fg=RENK_YESIL, font=("Segoe UI", 13, "bold")).pack(padx=16, pady=12, anchor="w")

        columns = ("tarih", "masa", "toplam", "odeme")
        tree = ttk.Treeview(container, columns=columns, show="headings", height=18)
        tree.heading("tarih", text="Tarih")
        tree.heading("masa", text="Masa")
        tree.heading("toplam", text="Toplam (TL)")
        tree.heading("odeme", text="Ödeme")
        tree.column("tarih", width=160)
        tree.column("masa", width=140)
        tree.column("toplam", width=120, anchor="e")
        tree.column("odeme", width=140)
        tree.pack(fill="both", expand=True)

        kayitlar = self.db.tum_satis_gecmisi()
        kayit_map = {}
        for k in kayitlar:
            iid = tree.insert("", "end", values=(k["tarih"].replace("T", " "), k["masa_isim"],
                                                    f"{k['toplam']:.2f}", k["odeme_tipi"]))
            kayit_map[iid] = k

        def detay_goster(event):
            sec = tree.selection()
            if not sec:
                return
            kayit = kayit_map[sec[0]]
            pencere = tk.Toplevel(self)
            pencere.title("Adisyon Detayı")
            pencere.configure(bg="white")
            pencere.geometry("340x420")
            metin = tk.Text(pencere, bg="white", fg="black", font=("Consolas", 11), bd=0)
            metin.pack(fill="both", expand=True, padx=10, pady=10)
            icerik = f"{kayit['masa_isim']}\n{kayit['tarih'].replace('T', ' ')}\n"
            icerik += f"Ödeme: {kayit['odeme_tipi']}\n" + "-" * 30 + "\n"
            icerik += kayit["detay"] + "\n" + "-" * 30 + "\n"
            icerik += f"TOPLAM: {kayit['toplam']:.2f} TL"
            metin.insert("1.0", icerik)
            metin.config(state="disabled")

        tree.bind("<Double-1>", detay_goster)

        tk.Label(container, text="(Detay için bir kayda çift tıklayın)", bg=RENK_BG,
                 fg=RENK_METIN_SOFT, font=FONT_KUCUK).pack(anchor="w", pady=(6, 0))


if __name__ == "__main__":
    app = AdisyonUygulamasi()
    app.mainloop()
