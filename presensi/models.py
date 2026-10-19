from django.db import models
from django.utils import timezone

class OPD(models.Model):
    nama_opd = models.CharField(max_length=150, unique=True)
    singkatan = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return self.nama_opd

class Presensi(models.Model):
    opd = models.ForeignKey(OPD, on_delete=models.CASCADE, related_name='data_presensi')
    nama = models.CharField(max_length=150)
    nip = models.CharField(max_length=30)  # Untuk validasi 1x per OPD
    jabatan = models.CharField(max_length=100, blank=True, null=True)
    waktu_submit = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('opd', 'nip')  # Mencegah presensi > 1 kali di OPD yang sama

    def __str__(self):
        return f"{self.nama} - {self.opd.nama_opd}"
        
# Model baru untuk menyimpan data skor DMS pegawai
class DMSPegawai(models.Model):
    nip = models.CharField(max_length=50, unique=True)
    nama = models.CharField(max_length=255)
    skor = models.FloatField(default=0.0)  # Skor talenta / DMS
    opd_induk = models.CharField(max_length=255, blank=True, null=True)
    unit_kerja = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.nama} ({self.nip})"

#model untuk landing
class LandingPageSetting(models.Model):
    judul_acara = models.CharField(max_length=255, default="Rakor Kepegawaian Tahun 2026")
    subjudul_acara = models.TextField(default="Badan Kepegawaian dan Pengembangan Sumber Daya Manusia Kota Metro")
    kode_sesi = models.CharField(max_length=50, default="RAKOR.2026")
    tagline_poster = models.CharField(max_length=255, default="Bumi Sai Wawai")
    quote_poster = models.TextField(default='"Penguatan Tata Kelola Manajemen ASN yang Akuntabel, Digital, dan Berbasis Data"')
    
    # Status Keaktifan Event di Halaman Utama (Ditambahkan untuk Multi-Event)
    is_active = models.BooleanField(default=True, help_text="Centang untuk mengaktifkan event ini di Landing Page utama")

    # 1. Jadwal Presensi
    presensi_buka = models.DateTimeField(null=True, blank=True, help_text="Waktu presensi dibuka (Contoh: 2026-10-23 08:00)")
    presensi_tutup = models.DateTimeField(null=True, blank=True, help_text="Waktu presensi ditutup (Contoh: 2026-10-23 16:00)")
    
    # 2. Zoom & Virtual Background
    zoom_url = models.URLField(blank=True, null=True, help_text="Link Zoom Meeting")
    vb_url = models.URLField(blank=True, null=True, help_text="Link Download Virtual Background")
    
    # 3. Jadwal Materi
    materi_url = models.URLField(blank=True, null=True, help_text="Link Unduh Materi / Dokumen")
    materi_buka = models.DateTimeField(null=True, blank=True, help_text="Waktu materi bisa diunduh")
    materi_tutup = models.DateTimeField(null=True, blank=True, help_text="Waktu materi ditutup")

    flyer_img = models.ImageField(upload_to="flyer/", blank=True, null=True, help_text="Upload Gambar Flyer Utama")
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = "Pengaturan Landing Page"
        verbose_name_plural = "Pengaturan Landing Page"

    def is_presensi_open(self):
        now = timezone.now()
        if self.presensi_buka and now < self.presensi_buka:
            return False, "Belum Dibuka"
        if self.presensi_tutup and now > self.presensi_tutup:
            return False, "Sudah Ditutup"
        return True, "Buka"

    def is_materi_open(self):
        now = timezone.now()
        if self.materi_buka and now < self.materi_buka:
            return False, "Belum Dibuka"
        if self.materi_tutup and now > self.materi_tutup:
            return False, "Sudah Ditutup"
        return True, "Buka"

    def __str__(self):
        status = " [AKTIF]" if self.is_active else ""
        return f"{self.judul_acara}{status}"