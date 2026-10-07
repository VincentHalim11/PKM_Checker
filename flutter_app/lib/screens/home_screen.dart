import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../services/validator_service.dart';
import '../widgets/validation_check_card.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  String? _selectedPdfPath;
  String _selectedScheme = 'K';

  String _status = 'Belum diuji';
  bool _isLoading = false;
  String? _error;

  Map<String, dynamic>? _validationResult;

  // ==========================================================
  // PILIH PDF
  // ==========================================================

  Future<void> _pickPdf() async {
    final file = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
    );

    if (file != null && file.path != null) {
      setState(() {
        _selectedPdfPath = file.path;
        _status = 'Belum diuji';
        _error = null;
        _validationResult = null;
      });
    }
  }

  // ==========================================================
  // JALANKAN VALIDATOR
  // ==========================================================

  Future<void> _runValidator() async {
    if (_selectedPdfPath == null) {
      setState(() {
        _error = 'Silakan pilih file PDF terlebih dahulu.';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _status = 'Sedang memeriksa...';
      _error = null;
      _validationResult = null;
    });

    try {
      final result = await ValidatorService.validate(
        pdfPath: _selectedPdfPath!,
        scheme: _selectedScheme,
      );

    setState(() {
      _validationResult = result;
      _status = result['status']?.toString() ?? 'UNKNOWN';

      if (_status == 'ERROR') {
        _error = result['error']?.toString();
      }
    });
    } catch (e) {
      setState(() {
        _status = 'ERROR';
        _error = e.toString();
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  // ==========================================================
  // NAMA FILE
  // ==========================================================

  String get _fileName {
    if (_selectedPdfPath == null) {
      return 'Belum ada file dipilih';
    }

    final path = _selectedPdfPath!;

    return path.split(RegExp(r'[\\/]')).last;
  }

  // ==========================================================
  // STATUS COLOR
  // ==========================================================

  Color _statusColor() {
    switch (_status) {
      case 'PASS':
        return Colors.green;
      case 'FAIL':
        return Colors.red;
      case 'REVIEW':
        return Colors.orange;
      case 'ERROR':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  // ==========================================================
  // STATUS TITLE
  // ==========================================================

  String _statusTitle() {
    switch (_status) {
      case 'PASS':
        return 'DOKUMEN SESUAI';

      case 'FAIL':
        return 'DOKUMEN PERLU PERBAIKAN';

      case 'REVIEW':
        return 'DOKUMEN MEMERLUKAN REVIEW';

      case 'ERROR':
        return 'TERJADI KESALAHAN';

      case 'Sedang memeriksa...':
        return 'SEDANG MEMERIKSA';

      default:
        return 'BELUM DIPERIKSA';
    }
  }

  IconData _statusIcon() {
    switch (_status) {
      case 'PASS':
        return Icons.check_circle;

      case 'FAIL':
        return Icons.cancel;

      case 'REVIEW':
        return Icons.warning;

      case 'ERROR':
        return Icons.error;

      default:
        return Icons.info_outline;
    }
  }

  // ==========================================================
  // HASIL PEMERIKSAAN
  // ==========================================================

  Widget _buildValidationResults() {
    if (_validationResult == null) {
      return const SizedBox.shrink();
    }

    final checks = _validationResult!['checks'];

    if (checks is! Map) {
      return const SizedBox.shrink();
    }

    final definitions = [
      {'key': 'page_size', 'title': 'Ukuran Kertas'},
      {'key': 'font', 'title': 'Jenis Font'},
      {'key': 'font_size', 'title': 'Ukuran Font'},
      {'key': 'margin', 'title': 'Margin'},
      {'key': 'line_spacing', 'title': 'Jarak Baris'},
      {'key': 'alignment', 'title': 'Perataan Paragraf'},
      {'key': 'page_number_font', 'title': 'Font Nomor Halaman'},
      {'key': 'page_number_position', 'title': 'Posisi Nomor Halaman'},
      {'key': 'page_number_sequence', 'title': 'Urutan Nomor Halaman'},
      {'key': 'page_number_coverage', 'title': 'Cakupan Nomor Halaman'},
      {'key': 'front_matter', 'title': 'Halaman Awal'},
      {'key': 'core_pages', 'title': 'Bagian Inti'},
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: 35),

        const Text(
          'Hasil Pemeriksaan',
          style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
        ),

        const SizedBox(height: 15),

        for (final definition in definitions)
          _buildCheckCard(
            checks,
            definition['key']!.toString(),
            definition['title']!.toString(),
          ),
      ],
    );
  }

  String _getSummary(String key, String status) {
    // REVIEW bukan pelanggaran: validator ragu dan butuh pemeriksaan manual.
    // Tanpa cabang ini, REVIEW ikut menampilkan kalimat "tidak sesuai".
    if (status == 'REVIEW') {
      return 'Belum bisa dipastikan otomatis; periksa manual (lihat detail).';
    }

    if (status != 'PASS' && status != 'FAIL') {
      return 'Status pemeriksaan tidak dikenali.';
    }

    switch (key) {
      case 'page_size':
        return status == 'PASS'
            ? 'Semua halaman menggunakan ukuran A4.'
            : 'Terdapat halaman yang tidak menggunakan ukuran A4.';

      case 'font':
        return status == 'PASS'
            ? 'Semua teks menggunakan Times New Roman.'
            : 'Ditemukan font yang tidak sesuai aturan.';

      case 'font_size':
        return status == 'PASS'
            ? 'Ukuran font sudah sesuai aturan.'
            : 'Terdapat ukuran font yang tidak sesuai aturan.';

      case 'margin':
        return status == 'PASS'
            ? 'Tidak ditemukan pelanggaran margin.'
            : 'Ditemukan konten yang melewati batas margin.';

      case 'line_spacing':
        return status == 'PASS'
            ? 'Jarak baris sudah sesuai aturan.'
            : 'Terdapat jarak baris yang tidak sesuai.';

      case 'alignment':
        return status == 'PASS'
            ? 'Paragraf sudah rata kiri-kanan.'
            : 'Terdapat paragraf yang tidak rata kiri-kanan.';

      case 'page_number_font':
        return status == 'PASS'
            ? 'Font nomor halaman sudah sesuai.'
            : 'Font nomor halaman tidak sesuai aturan.';

      case 'page_number_position':
        return status == 'PASS'
            ? 'Posisi nomor halaman sudah sesuai.'
            : 'Terdapat nomor halaman pada posisi yang salah.';

      case 'page_number_sequence':
        return status == 'PASS'
            ? 'Urutan nomor halaman sudah sesuai.'
            : 'Urutan nomor halaman tidak sesuai aturan.';

      case 'page_number_coverage':
        return status == 'PASS'
            ? 'Cakupan nomor halaman sudah sesuai.'
            : 'Terdapat halaman yang belum memiliki nomor.';

      case 'front_matter':
        return status == 'PASS'
            ? 'Struktur halaman awal sudah sesuai aturan.'
            : 'Ditemukan bagian awal yang tidak sesuai aturan.';

      case 'core_pages':
        return status == 'PASS'
            ? 'Jumlah halaman bagian inti sesuai aturan.'
            : 'Jumlah halaman bagian inti tidak sesuai aturan.';

      default:
        return 'Pemeriksaan selesai.';
    }
  }

  Widget _buildCheckCard(Map checks, String key, String title) {
    final check = checks[key];

    if (check is! Map) {
      return const SizedBox.shrink();
    }

    final status = check['status']?.toString() ?? 'UNKNOWN';

    final message = check['message']?.toString() ?? '';

    final details = check['details'];

    final summary = _getSummary(key, status);

    return ValidationCheckCard(
      title: title,
      status: status,
      summary: summary,
      message: message,
      details: details,
    );
  }

  // ==========================================================
  // UI
  // ==========================================================

  @override
  Widget build(BuildContext context) {
    final statusColor = _statusColor();

    return Scaffold(
      backgroundColor: Colors.grey.shade100,

      appBar: AppBar(
        title: const Text(
          'PKM 2026 Checker',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: false,
      ),

      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(32),

          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1000),

            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,

              children: [
                // ==================================================
                // HEADER
                // ==================================================

                const Text(
                  'PKM 2026 Checker',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 34, fontWeight: FontWeight.bold),
                ),

                const SizedBox(height: 8),

                Text(
                  'Pemeriksaan format proposal PKM secara otomatis',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 16, color: Colors.grey.shade700),
                ),

                const SizedBox(height: 35),

                // ==================================================
                // DOKUMEN
                // ==================================================
                Card(
                  elevation: 1,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),

                  child: Padding(
                    padding: const EdgeInsets.all(22),

                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,

                      children: [
                        const Text(
                          'Dokumen PDF',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),

                        const SizedBox(height: 12),

                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 14,
                          ),

                          decoration: BoxDecoration(
                            border: Border.all(color: Colors.grey.shade300),
                            borderRadius: BorderRadius.circular(10),
                          ),

                          child: Row(
                            children: [
                              const Icon(
                                Icons.picture_as_pdf,
                                color: Colors.red,
                              ),

                              const SizedBox(width: 12),

                              Expanded(
                                child: Text(
                                  _fileName,
                                  overflow: TextOverflow.ellipsis,

                                  style: const TextStyle(fontSize: 15),
                                ),
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 15),

                        OutlinedButton.icon(
                          onPressed: _isLoading ? null : _pickPdf,

                          icon: const Icon(Icons.folder_open),

                          label: Text(
                            _selectedPdfPath == null
                                ? 'Pilih PDF'
                                : 'Ganti PDF',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 20),

                // ==================================================
                // SKEMA
                // ==================================================
                Card(
                  elevation: 1,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),

                  child: Padding(
                    padding: const EdgeInsets.all(22),

                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,

                      children: [
                        const Text(
                          'Skema PKM',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),

                        const SizedBox(height: 12),

                        DropdownButtonFormField<String>(
                          initialValue: _selectedScheme,

                          decoration: const InputDecoration(
                            border: OutlineInputBorder(),
                            contentPadding: EdgeInsets.symmetric(
                              horizontal: 15,
                              vertical: 14,
                            ),
                          ),

                          items: const [
                            DropdownMenuItem(
                              value: 'GFT',
                              child: Text('PKM-GFT'),
                            ),
                            DropdownMenuItem(
                              value: 'AI',
                              child: Text('PKM-AI'),
                            ),
                            DropdownMenuItem(value: 'K', child: Text('PKM-K')),
                            DropdownMenuItem(
                              value: 'KC',
                              child: Text('PKM-KC'),
                            ),
                            DropdownMenuItem(
                              value: 'KI',
                              child: Text('PKM-KI'),
                            ),
                            DropdownMenuItem(
                              value: 'PI',
                              child: Text('PKM-PI'),
                            ),
                            DropdownMenuItem(
                              value: 'PM',
                              child: Text('PKM-PM'),
                            ),
                            DropdownMenuItem(
                              value: 'RE',
                              child: Text('PKM-RE'),
                            ),
                            DropdownMenuItem(
                              value: 'RSH',
                              child: Text('PKM-RSH'),
                            ),
                            DropdownMenuItem(
                              value: 'VGK',
                              child: Text('PKM-VGK'),
                            ),
                          ],

                          onChanged: _isLoading
                              ? null
                              : (value) {
                                  if (value != null) {
                                    setState(() {
                                      _selectedScheme = value;
                                      _status = 'Belum diuji';
                                      _error = null;
                                      _validationResult = null;
                                    });
                                  }
                                },
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 20),

                // ==================================================
                // BUTTON
                // ==================================================
                SizedBox(
                  height: 52,

                  child: ElevatedButton.icon(
                    onPressed: _isLoading ? null : _runValidator,

                    icon: Icon(
                      _isLoading ? Icons.hourglass_top : Icons.fact_check,
                    ),

                    label: Text(
                      _isLoading ? 'Sedang memeriksa...' : 'Periksa Dokumen',
                    ),

                    style: ElevatedButton.styleFrom(
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),

                      textStyle: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 25),

                // ==================================================
                // STATUS
                // ==================================================
                if (_status != 'Belum diuji' &&
                    _status != 'Sedang memeriksa...')
                  Card(
                    elevation: 1,

                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),

                    child: Container(
                      padding: const EdgeInsets.all(22),

                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: statusColor.withValues(alpha: 0.25),
                        ),
                      ),

                      child: Row(
                        children: [
                          Icon(_statusIcon(), color: statusColor, size: 42),

                          const SizedBox(width: 15),

                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,

                              children: [
                                Text(
                                  _statusTitle(),
                                  style: TextStyle(
                                    fontSize: 20,
                                    fontWeight: FontWeight.bold,
                                    color: statusColor,
                                  ),
                                ),

                                const SizedBox(height: 5),

                                Text(
                                  'Status akhir pemeriksaan: $_status',
                                  style: TextStyle(color: Colors.grey.shade700),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                if (_isLoading)
                  const Padding(
                    padding: EdgeInsets.only(top: 25),
                    child: Column(
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(height: 12),
                        Text('Validator sedang memeriksa dokumen...'),
                      ],
                    ),
                  ),

                // ==================================================
                // ERROR
                // ==================================================
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 20),

                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(18),

                        child: Row(
                          children: [
                            const Icon(Icons.error_outline, color: Colors.red),

                            const SizedBox(width: 12),

                            Expanded(child: Text(_error!)),
                          ],
                        ),
                      ),
                    ),
                  ),

                // ==================================================
                // RESULTS
                // ==================================================
                _buildValidationResults(),

                const SizedBox(height: 40),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
