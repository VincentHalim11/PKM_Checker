import 'package:flutter/material.dart';

class ValidationCheckCard extends StatelessWidget {
  final String title;
  final String status;
  final String summary;
  final String message;
  final dynamic details;

  const ValidationCheckCard({
    super.key,
    required this.title,
    required this.status,
    required this.summary,
    required this.message,
    this.details,
  });

  IconData _getIcon() {
    switch (status) {
      case 'PASS':
        return Icons.check_circle;
      case 'FAIL':
        return Icons.cancel;
      case 'REVIEW':
        return Icons.warning;
      default:
        return Icons.help;
    }
  }

  Color _getColor() {
    switch (status) {
      case 'PASS':
        return Colors.green;
      case 'FAIL':
        return Colors.red;
      case 'REVIEW':
        return Colors.orange;
      default:
        return Colors.grey;
    }
  }

  bool get _hasDetails {
    if (details == null) {
      return false;
    }

    // Ukuran Font dapat memuat daftar ukuran isi dan caption.
    // Jangan membuka bagian Detail jika keduanya kosong (mis. hasil PASS).
    if (title == 'Ukuran Font' && details is Map) {
      final bodyItems = details['body'];
      final captionItems = details['caption'];
      return (bodyItems is List && bodyItems.isNotEmpty) ||
          (captionItems is List && captionItems.isNotEmpty);
    }

    if (title == 'Font Nomor Halaman' && details is Map) {
      final badItems = details['bad'];
      final missingPages = details['pages_without_number'];
      return (badItems is List && badItems.isNotEmpty) ||
          (missingPages is List && missingPages.isNotEmpty);
    }

    if (details is Map) {
      return details.isNotEmpty;
    }

    if (details is List) {
      return details.isNotEmpty;
    }

    return true;
  }

  // ==========================================================
  // FORMAT LABEL
  // ==========================================================

  String _formatLabel(String value) {
    return value
        .replaceAll('_', ' ')
        .split(' ')
        .map(
          (word) => word.isEmpty
              ? word
              : '${word[0].toUpperCase()}${word.substring(1)}',
        )
        .join(' ');
  }

  // ==========================================================
  // FORMAT VALUE
  // ==========================================================

  String _formatValue(dynamic value) {
    if (value == null) {
      return '-';
    }

    if (value is List) {
      return value.join(', ');
    }

    return value.toString();
  }

  int? _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '');
  }

  double? _toDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '');
  }

  String _formatPercent(dynamic value) {
    if (value is! num) return 'Tidak tersedia';
    var result = (value * 100).toStringAsFixed(1);
    if (result.endsWith('.0')) {
      result = result.substring(0, result.length - 2);
    }
    return '${result.replaceAll('.', ',')}%';
  }

  String _compactPageNumbers(List<int> pages) {
    if (pages.isEmpty) return 'Tidak ada';

    final sorted = pages.toSet().toList()..sort();
    final ranges = <String>[];
    var start = sorted.first;
    var end = start;

    for (final page in sorted.skip(1)) {
      if (page == end + 1) {
        end = page;
      } else {
        ranges.add(start == end ? '$start' : '$start–$end');
        start = page;
        end = page;
      }
    }

    ranges.add(start == end ? '$start' : '$start–$end');
    return ranges.join(', ');
  }

  String _formatNumberingStyle(String value) {
    switch (value.toLowerCase()) {
      case 'arabic':
        return 'Angka Arab';
      case 'roman':
      case 'roman_upper':
      case 'roman_uppercase':
        return 'Angka Romawi kapital';
      case 'roman_lower':
      case 'roman_lowercase':
        return 'Angka Romawi kecil';
      default:
        return _formatLabel(value);
    }
  }

  Widget _detailRow(String label, String detailValue) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(detailValue),
        ],
      ),
    );
  }

  Widget _buildAlignmentDetails(dynamic value) {
    if (value is! Map) {
      return const Text('Detail perataan paragraf tidak tersedia.');
    }

    final share = value['share'];
    final nLines = _toInt(value['n_lines']);
    final offPagesRaw = value['off_pages'];
    final offPages = <int>[];
    if (offPagesRaw is List) {
      for (final item in offPagesRaw) {
        final page = _toInt(item);
        if (page != null) offPages.add(page);
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _detailRow('Baris dengan tepi kanan konsisten', _formatPercent(share)),
        if (nLines != null)
          _detailRow('Baris yang dianalisis', '$nLines baris'),
        if (offPages.isNotEmpty)
          _detailRow(
            'Halaman yang perlu diperiksa',
            _compactPageNumbers(offPages),
          ),
        _detailRow(
          'Kesimpulan',
          status == 'PASS'
              ? 'Pola tepi kanan memenuhi kriteria pemeriksaan otomatis.'
              : status == 'FAIL'
              ? 'Pola tepi kanan belum memenuhi kriteria rata kiri-kanan. Periksa halaman yang tercantum di atas.'
              : 'Hasil otomatis belum cukup untuk memastikan perataan paragraf; periksa manual.',
        ),
      ],
    );
  }

  Widget _buildPageNumberPositionDetails(dynamic value) {
    if (value is! Map) {
      return const Text('Detail posisi nomor halaman tidak tersedia.');
    }

    final badRaw = value['bad'];
    final badRows = <List>[];
    if (badRaw is List) {
      for (final row in badRaw) {
        if (row is List) badRows.add(row);
      }
    }

    final missingRaw = value['pages_without_number'];
    final missingPages = <int>[];
    if (missingRaw is List) {
      for (final item in missingRaw) {
        final page = _toInt(item);
        if (page != null) missingPages.add(page);
      }
    }

    final physicalPages = <int>[];
    final styles = <String>{};
    final positions = <String>{};
    for (final row in badRows) {
      if (row.isNotEmpty) {
        final page = _toInt(row[0]);
        if (page != null) physicalPages.add(page);
      }
      if (row.length > 2 && row[2] != null) {
        styles.add(_formatNumberingStyle(row[2].toString()));
      }
      if (row.length > 3 && row[3] != null) {
        positions.add(row[3].toString());
      }
    }

    final match = RegExp(r'(\d+)\s+dari\s+(\d+)\s+nomor').firstMatch(message);
    final totalNumbers = match == null
        ? null
        : int.tryParse(match.group(2) ?? '');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _detailRow(
          'Nomor halaman pada posisi yang salah',
          totalNumbers == null
              ? '${badRows.length} nomor'
              : '${badRows.length} dari $totalNumbers nomor',
        ),
        if (styles.isNotEmpty) _detailRow('Jenis penomoran', styles.join(', ')),
        if (positions.isNotEmpty)
          _detailRow('Posisi yang terdeteksi', positions.join(', ')),
        if (physicalPages.isNotEmpty)
          _detailRow(
            'Halaman fisik yang perlu diperiksa',
            _compactPageNumbers(physicalPages),
          ),
        _detailRow('Halaman tanpa nomor', _compactPageNumbers(missingPages)),
        _detailRow(
          'Kesimpulan',
          status == 'PASS'
              ? 'Posisi nomor halaman yang terdeteksi sesuai aturan skema.'
              : status == 'FAIL'
              ? 'Pindahkan nomor halaman pada halaman yang tercantum agar sesuai dengan aturan skema.'
              : 'Posisi nomor halaman belum dapat dipastikan secara otomatis; periksa manual.',
        ),
      ],
    );
  }

  String _displayMessage() {
    if (title == 'Bagian Inti' && details is Map) {
      final data = details as Map;
      final detectedMin = _toInt(data['min_pages']);
      final detectedMax = _toInt(data['max_pages']);
      final ruleMin = _toInt(data['rule_min']);
      final ruleMax = _toInt(data['rule_max']);
      final scheme = data['scheme']?.toString();

      final detected = detectedMin != null && detectedMax != null
          ? detectedMin == detectedMax
                ? '$detectedMin halaman'
                : '$detectedMin–$detectedMax halaman'
          : 'belum dapat ditentukan';
      final rule = ruleMin != null && ruleMin > 0 && ruleMax != null
          ? 'batas $ruleMin–$ruleMax halaman'
          : ruleMin != null && ruleMin > 0
          ? 'minimal $ruleMin halaman'
          : ruleMax != null
          ? 'maksimal $ruleMax halaman'
          : 'batas halaman tidak tersedia';
      final schemeLabel = scheme == null || scheme.isEmpty
          ? ''
          : scheme.toUpperCase() == 'GENERAL'
          ? ' untuk aturan umum'
          : ' untuk PKM-${scheme.toUpperCase()}';

      if (status == 'PASS') {
        return 'Bagian inti terdeteksi $detected; sesuai dengan $rule$schemeLabel.';
      }
      if (status == 'FAIL') {
        return 'Bagian inti terdeteksi $detected; tidak sesuai dengan $rule$schemeLabel.';
      }
    }

    if (title == 'Posisi Nomor Halaman' && status == 'FAIL') {
      final match = RegExp(r'(\d+)\s+dari\s+(\d+)\s+nomor').firstMatch(message);
      if (match != null) {
        return '${match.group(1)} dari ${match.group(2)} nomor halaman terdeteksi pada posisi yang tidak sesuai aturan.';
      }
      return 'Ditemukan nomor halaman pada posisi yang tidak sesuai aturan skema.';
    }

    if (title == 'Font Nomor Halaman' && status == 'FAIL') {
      final data = details;
      final bad = data is Map ? data['bad'] : null;
      final badCount = bad is List ? bad.length : 0;
      final match = RegExp(r'(\d+)\s+dari\s+(\d+)\s+nomor').firstMatch(message);
      final total = match == null ? null : int.tryParse(match.group(2) ?? '');
      if (badCount > 0) {
        return total == null
            ? '$badCount nomor halaman tidak sesuai ketentuan Times New Roman 12 pt.'
            : '$badCount dari $total nomor halaman tidak sesuai ketentuan Times New Roman 12 pt.';
      }
      return 'Font atau ukuran nomor halaman tidak sesuai ketentuan Times New Roman 12 pt.';
    }

    if (title == 'Perataan Paragraf' && details is Map) {
      final data = details as Map;
      final share = data['share'];
      final nLines = _toInt(data['n_lines']);
      if (share is num && nLines != null) {
        if (status == 'FAIL') {
          return 'Hanya ${_formatPercent(share)} dari $nLines baris lanjutan yang berakhir pada tepi kanan yang sama.';
        }
        if (status == 'PASS') {
          return '${_formatPercent(share)} dari $nLines baris lanjutan berakhir pada tepi kanan yang sama.';
        }
      }
    }

    return message;
  }

  String _formatRatio(dynamic value) {
    if (value is! num) return 'Tidak tersedia';
    return value.toStringAsFixed(2).replaceAll('.', ',');
  }

  Widget _buildLineSpacingDetails(dynamic value) {
    if (value is! Map) {
      return const Text('Detail jarak baris tidak tersedia.');
    }

    final expected = value['expected'];
    final nGaps = _toInt(value['n_single']);
    final shareOk = value['share_ok'];
    final dominantRatio = value['dominant_ratio'];
    final warning = value['warning']?.toString().trim();

    final offPages = <int>[];
    final rawOffPages = value['off_pages'];
    if (rawOffPages is List) {
      for (final item in rawOffPages) {
        final page = _toInt(item);
        if (page != null) offPages.add(page);
      }
    }

    final expectedText = expected is num
        ? '${_formatRatio(expected)} ± 0,05'
        : 'Aturan tidak tersedia';

    String conclusion;
    switch (status) {
      case 'PASS':
        conclusion =
            'Hasil pemeriksaan otomatis memenuhi kriteria jarak baris.';
        break;
      case 'FAIL':
        conclusion = 'Jarak baris terdeteksi tidak sesuai aturan. Periksa halaman yang disebutkan di atas.';
        break;
      case 'REVIEW':
        conclusion = 'Bukti yang tersedia belum cukup untuk memastikan jarak baris secara otomatis. Silakan periksa dokumen secara manual.';
        break;
      default:
        conclusion = 'Hasil pemeriksaan jarak baris belum dapat disimpulkan.';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _detailRow('Aturan jarak baris', expectedText),
        if (nGaps != null)
          _detailRow('Celah baris yang dianalisis', '$nGaps celah'),
        if (shareOk is num)
          _detailRow('Celah baris yang sesuai aturan', _formatPercent(shareOk)),
        if (dominantRatio is num)
          _detailRow(
            'Jarak baris yang paling sering terdeteksi',
            _formatRatio(dominantRatio),
          ),
        if (status == 'FAIL' && offPages.isNotEmpty)
          _detailRow(
            'Halaman yang perlu diperiksa',
            _compactPageNumbers(offPages),
          ),
        if (warning != null && warning.isNotEmpty && warning != '-')
          _detailRow('Catatan pemeriksaan', warning),
        _detailRow('Kesimpulan', conclusion),
      ],
    );
  }

  // ==========================================================
  // DETAIL BAGIAN INTI
  // ==========================================================

  Widget _buildCorePagesDetails(dynamic value) {
    if (value is! Map) {
      return const Text('Detail jumlah halaman bagian inti tidak tersedia.');
    }

    int? toInt(dynamic raw) {
      if (raw is int) return raw;
      if (raw is num) return raw.round();
      return int.tryParse(raw?.toString() ?? '');
    }

    final detectedMin = toInt(value['min_pages']);
    final detectedMax = toInt(value['max_pages']);
    final ruleMin = toInt(value['rule_min']);
    final ruleMax = toInt(value['rule_max']);
    final physicalStart = toInt(value['physical_start']);
    final scheme = value['scheme']?.toString();

    String detectedPages;
    if (detectedMin != null &&
        detectedMax != null &&
        detectedMin == detectedMax) {
      detectedPages = '$detectedMin halaman';
    } else if (detectedMin != null && detectedMax != null) {
      detectedPages = '$detectedMin–$detectedMax halaman';
    } else if (detectedMin != null) {
      detectedPages = 'Sekurang-kurangnya $detectedMin halaman';
    } else if (detectedMax != null) {
      detectedPages = 'Hingga $detectedMax halaman';
    } else {
      detectedPages = 'Belum dapat ditentukan otomatis';
    }

    final hasMinimumRule = ruleMin != null && ruleMin > 0;
    String allowedPages;
    if (hasMinimumRule && ruleMax != null) {
      allowedPages = '$ruleMin–$ruleMax halaman';
    } else if (hasMinimumRule) {
      allowedPages = 'Minimal $ruleMin halaman';
    } else if (ruleMax != null) {
      allowedPages = 'Maksimal $ruleMax halaman';
    } else {
      allowedPages = 'Batas halaman tidak tersedia';
    }

    String schemeLabel = 'Tidak diketahui';
    if (scheme != null && scheme.isNotEmpty) {
      schemeLabel = scheme.toUpperCase() == 'GENERAL'
          ? 'Umum (GENERAL)'
          : 'PKM-${scheme.toUpperCase()}';
    }

    Widget detailRow(String label, String detailValue) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            Text(detailValue),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        detailRow('Jumlah halaman bagian inti', detectedPages),
        detailRow('Batas sesuai aturan', allowedPages),
        if (physicalStart != null)
          detailRow('Bagian inti dimulai pada halaman fisik', '$physicalStart'),
        if (scheme != null && scheme.isNotEmpty)
          detailRow('Skema', schemeLabel),
      ],
    );
  }

  // ==========================================================
  // DETAIL JENIS FONT
  // ==========================================================

  Widget _buildFontDetails(dynamic value) {
    if (value is! List || value.isEmpty) {
      return const Text('Tidak ditemukan font yang melanggar aturan.');
    }

    final fontItems = value.whereType<Map>().toList();
    if (fontItems.isEmpty) {
      return const Text('Detail font yang tidak sesuai tidak tersedia.');
    }

    Widget fontCard(Map item) {
      final fontName = item['font']?.toString() ?? 'Nama font tidak tersedia';
      final count = _toInt(item['count']);

      return Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Jenis font terdeteksi',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            SelectableText(fontName),
            const SizedBox(height: 12),
            const Text(
              'Jumlah kemunculan',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(count == null ? 'Jumlah tidak tersedia' : '$count kali'),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.only(bottom: 12),
          child: Text('Font yang diwajibkan: Times New Roman.'),
        ),
        for (final item in fontItems) fontCard(item),
      ],
    );
  }

  // ==========================================================
  // DETAIL UKURAN FONT
  // ==========================================================

  String _fontKindLabel(dynamic rawKind) {
    final kind = rawKind?.toString() ?? '';
    switch (kind) {
      case 'body':
        return 'Teks isi';
      case 'title':
        return 'Judul';
      case 'author':
        return 'Nama penulis';
      case 'abstract':
        return 'Abstrak';
      case 'abstract_heading':
        return 'Judul abstrak';
      case 'caption':
        return 'Keterangan gambar/tabel';
      case 'source':
        return 'Baris sumber';
      case 'table':
        return 'Isi tabel';
      default:
        return kind.isEmpty
            ? 'Kategori teks tidak tersedia'
            : _formatLabel(kind);
    }
  }

  String _formatFontSize(dynamic rawSize) {
    if (rawSize is! num) return 'Ukuran tidak tersedia';
    var formatted = rawSize.toStringAsFixed(2);
    formatted = formatted.replaceFirst(RegExp(r'\.?0+$'), '');
    return '${formatted.replaceAll('.', ',')} pt';
  }

  Widget _buildFontSizeDetails(dynamic value) {
    List<Map> bodyItems = [];
    List<Map> captionItems = [];

    // Struktur terbaru dari home_screen: {body: [...], caption: [...]}
    if (value is Map) {
      final body = value['body'];
      final captions = value['caption'];
      if (body is List) bodyItems = body.whereType<Map>().toList();
      if (captions is List) captionItems = captions.whereType<Map>().toList();
    } else if (value is List) {
      // Kompatibilitas dengan struktur lama.
      bodyItems = value.whereType<Map>().toList();
    }

    if (bodyItems.isEmpty && captionItems.isEmpty) {
      return const Text('Tidak ditemukan ukuran font yang melanggar aturan.');
    }

    Widget sizeCard(Map item) {
      final size = _formatFontSize(item['size']);
      final kind = _fontKindLabel(item['kind']);
      final count = _toInt(item['count']);
      final pages = <int>[];
      final rawPages = item['pages'];
      if (rawPages is List) {
        for (final rawPage in rawPages) {
          final page = _toInt(rawPage);
          if (page != null) pages.add(page);
        }
      }

      final samples = item['samples'];
      final sampleTexts = samples is List
          ? samples
                .map((sample) => sample.toString().trim())
                .where((sample) => sample.isNotEmpty)
                .take(3)
                .toList()
          : <String>[];

      return Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _detailRow('Ukuran font terdeteksi', size),
            _detailRow('Kategori teks', kind),
            if (count != null) _detailRow('Jumlah kemunculan', '$count kali'),
            if (pages.isNotEmpty)
              _detailRow('Halaman terdampak', _compactPageNumbers(pages)),
            if (sampleTexts.isNotEmpty) ...[
              const Text(
                'Contoh teks terdampak',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 6),
              for (final sample in sampleTexts)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    '“$sample”',
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Aturan ukuran font mengikuti ketentuan skema yang dipilih.',
        ),
        if (bodyItems.isNotEmpty) ...[
          const SizedBox(height: 12),
          const Text(
            'Ukuran font teks',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          const SizedBox(height: 8),
          for (final item in bodyItems) sizeCard(item),
        ],
        if (captionItems.isNotEmpty) ...[
          const SizedBox(height: 4),
          const Text(
            'Ukuran font keterangan gambar/tabel',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          const SizedBox(height: 8),
          for (final item in captionItems) sizeCard(item),
        ],
      ],
    );
  }

  // ==========================================================
  // DETAIL MARGIN
  // ==========================================================

  String _marginSideLabel(dynamic rawType) {
    switch ((rawType?.toString() ?? '').toUpperCase()) {
      case 'LEFT':
        return 'Kiri';
      case 'RIGHT':
        return 'Kanan';
      case 'TOP':
        return 'Atas';
      case 'BOTTOM':
        return 'Bawah';
      default:
        final type = rawType?.toString().trim() ?? '';
        return type.isEmpty ? 'Tidak diketahui' : _formatLabel(type);
    }
  }

  String _formatCentimeters(dynamic rawValue) {
    if (rawValue is! num) {
      final parsed = num.tryParse(rawValue?.toString() ?? '');
      if (parsed == null) return 'Tidak tersedia';
      return '${parsed.toStringAsFixed(2).replaceAll('.', ',')} cm';
    }
    return '${rawValue.toStringAsFixed(2).replaceAll('.', ',')} cm';
  }

  String _shortMarginText(dynamic rawText) {
    final value = rawText?.toString().trim() ?? '';
    if (value.isEmpty) return 'Contoh teks tidak tersedia';

    // Teks daftar isi terkadang sangat panjang; pertahankan isi awalnya saja.
    final normalized = value.replaceAll(RegExp(r'\s+'), ' ');
    if (normalized.length <= 180) return normalized;
    return '${normalized.substring(0, 177)}…';
  }

  Widget _buildMarginFinding(Map item) {
    final position = item['position_cm'];
    final expected = item['expected_cm'];
    final textSample = _shortMarginText(item['text']);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _detailRow('Jarak teks dari tepi kertas', _formatCentimeters(position)),
        _detailRow(
          'Batas margin yang diwajibkan',
          _formatCentimeters(expected),
        ),
        const Text(
          'Contoh teks terdampak',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 3),
        Text('“$textSample”', maxLines: 3, overflow: TextOverflow.ellipsis),
      ],
    );
  }

  Widget _buildMarginGroup(Map<String, dynamic> group) {
    final pageLabel = group['page']?.toString() ?? 'tidak diketahui';
    final sideLabel = (group['side'] as String).toLowerCase();
    final items = group['items'] as List<Map>;
    const maxExamples = 2;
    final shownItems = items.take(maxExamples).toList();

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Halaman fisik $pageLabel · Margin $sideLabel',
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
          ),
          const SizedBox(height: 4),
          Text('${items.length} temuan'),
          const SizedBox(height: 10),
          for (var i = 0; i < shownItems.length; i++) ...[
            if (i > 0) const Divider(height: 20),
            _buildMarginFinding(shownItems[i]),
          ],
          if (items.length > maxExamples) ...[
            const Divider(height: 20),
            Text(
              '${items.length - maxExamples} temuan tambahan tidak ditampilkan agar rincian lebih ringkas.',
              style: TextStyle(color: Colors.grey.shade700),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildMarginDetails(dynamic value) {
    if (value is! List || value.isEmpty) {
      return const Text('Tidak ditemukan detail pelanggaran margin.');
    }

    final findings = value.whereType<Map>().toList();
    if (findings.isEmpty) {
      return const Text('Rincian temuan margin tidak tersedia.');
    }

    // Kelompokkan temuan berdasarkan halaman dan sisi margin agar
    // dialog tidak mengulang label yang sama untuk setiap baris teks.
    final grouped = <Map<String, dynamic>>[];
    for (final item in findings) {
      final page = _toInt(item['page']);
      final side = _marginSideLabel(item['type']);
      final index = grouped.indexWhere(
        (group) => group['page'] == page && group['side'] == side,
      );

      if (index >= 0) {
        (grouped[index]['items'] as List<Map>).add(item);
      } else {
        grouped.add({
          'page': page,
          'side': side,
          'items': <Map>[item],
        });
      }
    }

    final pages = <int>[];
    final sides = <String>{};
    for (final item in findings) {
      final page = _toInt(item['page']);
      if (page != null) pages.add(page);
      sides.add(_marginSideLabel(item['type']));
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('${findings.length} temuan konten terdeteksi pada area margin.'),
        const SizedBox(height: 8),
        if (pages.isNotEmpty)
          _detailRow(
            'Halaman yang perlu diperiksa',
            _compactPageNumbers(pages),
          ),
        if (sides.isNotEmpty)
          _detailRow('Sisi margin yang terpengaruh', sides.join(', ')),
        const SizedBox(height: 4),
        const Text(
          'Rincian temuan per halaman',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        const SizedBox(height: 10),
        for (final group in grouped) _buildMarginGroup(group),
      ],
    );
  }

  // ==========================================================
  // DETAIL UKURAN KERTAS
  // ==========================================================

  double? _pointsToCentimeters(dynamic value) {
    final points = _toDouble(value);
    if (points == null) return null;
    return points / 72 * 2.54;
  }

  String _formatCmNumber(double value) =>
      value.toStringAsFixed(2).replaceAll('.', ',');

  String _formatPointSize(dynamic value) {
    if (value is! num) return 'Ukuran tidak tersedia';
    var formatted = value.toStringAsFixed(2);
    formatted = formatted.replaceFirst(RegExp(r'\.?0+$'), '');
    return '${formatted.replaceAll('.', ',')} pt';
  }

  String _pageSizeName(double widthPt, double heightPt) {
    final shortSide = widthPt < heightPt ? widthPt : heightPt;
    final longSide = widthPt < heightPt ? heightPt : widthPt;

    if ((shortSide - 612).abs() <= 2 && (longSide - 792).abs() <= 2) {
      return 'Letter';
    }
    if ((shortSide - 595.28).abs() <= 3 && (longSide - 841.89).abs() <= 3) {
      return 'A4';
    }
    if ((shortSide - 612).abs() <= 2 && (longSide - 1008).abs() <= 3) {
      return 'Legal';
    }
    return 'Ukuran non-A4';
  }

  Widget _buildPageSizeDetails(dynamic value) {
    if (value is! List) {
      return const Text('Detail ukuran halaman tidak tersedia.');
    }

    final pages = value.whereType<Map>().toList();
    if (pages.isEmpty) {
      return const Text('Tidak ditemukan halaman dengan ukuran selain A4.');
    }

    final groups = <Map<String, dynamic>>[];
    for (final item in pages) {
      final width = _toDouble(item['width']);
      final height = _toDouble(item['height']);
      final page = _toInt(item['page']);
      if (width == null || height == null) continue;

      final key = '${width.toStringAsFixed(1)}x${height.toStringAsFixed(1)}';
      final index = groups.indexWhere((group) => group['key'] == key);
      if (index >= 0) {
        final groupPages = groups[index]['pages'] as List<int>;
        if (page != null) groupPages.add(page);
      } else {
        groups.add({
          'key': key,
          'width': width,
          'height': height,
          'pages': <int>[?page],
        });
      }
    }

    if (groups.isEmpty) {
      return const Text('Data ukuran halaman tidak dapat dibaca.');
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Ukuran halaman yang diwajibkan: A4 (21,00 × 29,70 cm).'),
        const SizedBox(height: 12),
        for (final group in groups) ...[
          Builder(
            builder: (context) {
              final widthPt = group['width'] as double;
              final heightPt = group['height'] as double;
              final widthCm = _pointsToCentimeters(widthPt)!;
              final heightCm = _pointsToCentimeters(heightPt)!;
              final pageList = group['pages'] as List<int>;
              final pageLabel = _compactPageNumbers(pageList);
              final sizeName = _pageSizeName(widthPt, heightPt);

              return Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Halaman fisik $pageLabel',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 10),
                    _detailRow(
                      'Ukuran terdeteksi',
                      '$sizeName (${_formatCmNumber(widthCm)} × ${_formatCmNumber(heightCm)} cm)',
                    ),
                    _detailRow(
                      'Ukuran yang diwajibkan',
                      'A4 (21,00 × 29,70 cm)',
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ],
    );
  }

  // ==========================================================
  // DETAIL URUTAN NOMOR HALAMAN
  // ==========================================================

  Widget _buildPageNumberSequenceDetails(dynamic value) {
    if (value is! List) {
      return const Text('Detail urutan nomor halaman tidak tersedia.');
    }

    final rows = value
        .whereType<List>()
        .where((row) => row.length >= 3)
        .toList();
    if (rows.isEmpty) {
      return const Text(
        'Tidak ditemukan ketidaksesuaian urutan nomor halaman.',
      );
    }

    final first = rows.first;
    final firstPhysical = _toInt(first[0]);
    final firstActual = _toInt(first[1]);
    final firstExpected = _toInt(first[2]);
    final firstStyle = first.length > 3 ? first[3]?.toString() : null;
    final offset = firstActual != null && firstExpected != null
        ? firstActual - firstExpected
        : null;
    final offsets = rows.map((row) {
      final actual = _toInt(row[1]);
      final expected = _toInt(row[2]);
      return actual != null && expected != null ? actual - expected : null;
    }).toList();
    final sameOffset =
        offset != null && offsets.every((item) => item == offset);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _detailRow(
          'Halaman fisik pertama yang perlu diperiksa',
          firstPhysical == null ? 'Tidak tersedia' : '$firstPhysical',
        ),
        _detailRow(
          'Nomor yang terdeteksi',
          firstActual == null ? 'Tidak tersedia' : '$firstActual',
        ),
        _detailRow(
          'Nomor yang seharusnya',
          firstExpected == null ? 'Tidak tersedia' : '$firstExpected',
        ),
        if (offset != null)
          _detailRow('Selisih penomoran', '${offset > 0 ? '+' : ''}$offset'),
        if (firstStyle != null && firstStyle.isNotEmpty)
          _detailRow('Jenis penomoran', _formatNumberingStyle(firstStyle)),
        _detailRow(
          'Jumlah halaman dengan urutan tidak sesuai',
          '${rows.length} halaman',
        ),
        const SizedBox(height: 4),
        const Text(
          'Contoh nomor halaman yang terdeteksi',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        for (final row in rows.take(3))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              'Halaman fisik ${_toInt(row[0]) ?? '?'}: '
              'tercetak ${_toInt(row[1]) ?? '?'}, '
              'seharusnya ${_toInt(row[2]) ?? '?'}',
            ),
          ),
        if (rows.length > 3)
          Text(
            sameOffset
                ? '${rows.length - 3} halaman lainnya menunjukkan pola selisih yang sama.'
                : '${rows.length - 3} temuan urutan lainnya tidak ditampilkan.',
            style: TextStyle(color: Colors.grey.shade700),
          ),
      ],
    );
  }

  // ==========================================================
  // DETAIL FONT NOMOR HALAMAN
  // ==========================================================

  String _displayPageNumberFontName(String rawName) {
    final normalized = rawName.toLowerCase().replaceAll(
      RegExp(r'[^a-z0-9]'),
      '',
    );
    if (normalized.startsWith('timesnewromanps') ||
        normalized == 'timesnewroman') {
      return 'Times New Roman';
    }
    return rawName;
  }

  Widget _buildPageNumberFontDetails(dynamic value) {
    if (value is! Map) {
      return const Text('Detail font nomor halaman tidak tersedia.');
    }

    final badRaw = value['bad'];
    final missingRaw = value['pages_without_number'];
    final badRows = badRaw is List
        ? badRaw.whereType<List>().where((row) => row.length >= 3).toList()
        : <List>[];
    final missingPages = <int>[];
    if (missingRaw is List) {
      for (final item in missingRaw) {
        final page = _toInt(item);
        if (page != null) missingPages.add(page);
      }
    }

    if (badRows.isEmpty && missingPages.isEmpty) {
      return const Text('Font dan ukuran nomor halaman memenuhi aturan.');
    }

    final groups = <Map<String, dynamic>>[];
    for (final row in badRows) {
      final page = _toInt(row[0]);
      final font = row[1]?.toString() ?? 'Font tidak diketahui';
      final size = _toDouble(row[2]);
      final key = '$font|${size?.toStringAsFixed(2) ?? 'unknown'}';
      final index = groups.indexWhere((group) => group['key'] == key);
      if (index >= 0) {
        final groupPages = groups[index]['pages'] as List<int>;
        if (page != null) groupPages.add(page);
      } else {
        groups.add({
          'key': key,
          'font': font,
          'size': size,
          'pages': <int>[?page],
        });
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Ketentuan: Times New Roman, 12 pt.'),
        const SizedBox(height: 12),
        for (final group in groups) ...[
          Container(
            width: double.infinity,
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.grey.shade300),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _detailRow(
                  'Font terdeteksi',
                  '${_displayPageNumberFontName(group['font'].toString())}'
                      '${_displayPageNumberFontName(group['font'].toString()) == group['font'].toString() ? '' : ' (nama internal: ${group['font']})'}',
                ),
                _detailRow(
                  'Ukuran terdeteksi',
                  _formatPointSize(group['size']),
                ),
                _detailRow(
                  'Jumlah nomor terdampak',
                  '${(group['pages'] as List<int>).length} nomor',
                ),
                _detailRow(
                  'Halaman fisik',
                  _compactPageNumbers(group['pages'] as List<int>),
                ),
                _detailRow(
                  'Ketentuan yang diwajibkan',
                  'Times New Roman, 12 pt',
                ),
              ],
            ),
          ),
        ],
        if (missingPages.isNotEmpty)
          _detailRow('Halaman tanpa nomor', _compactPageNumbers(missingPages)),
      ],
    );
  }

  // ==========================================================
  // BUILD DETAIL CONTENT
  // ==========================================================

  Widget _buildDetailsContent(dynamic value) {
    if (title == 'Jenis Font') {
      return _buildFontDetails(value);
    }

    if (title == 'Ukuran Font') {
      return _buildFontSizeDetails(value);
    }

    if (title == 'Margin') {
      return _buildMarginDetails(value);
    }

    if (title == 'Ukuran Kertas') {
      return _buildPageSizeDetails(value);
    }

    if (title == 'Urutan Nomor Halaman') {
      return _buildPageNumberSequenceDetails(value);
    }

    if (title == 'Font Nomor Halaman') {
      return _buildPageNumberFontDetails(value);
    }

    if (title == 'Bagian Inti') {
      return _buildCorePagesDetails(value);
    }

    if (title == 'Jarak Baris') {
      return _buildLineSpacingDetails(value);
    }

    if (title == 'Perataan Paragraf') {
      return _buildAlignmentDetails(value);
    }

    if (title == 'Posisi Nomor Halaman') {
      return _buildPageNumberPositionDetails(value);
    }

    if (value == null) {
      return const Text('Tidak ada detail tambahan.');
    }

    // --------------------------------------------------------
    // LIST
    // --------------------------------------------------------

    if (value is List) {
      if (value.isEmpty) {
        return const Text('Tidak ada detail tambahan.');
      }

      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final item in value) ...[
            if (item is Map)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.grey.shade300),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      for (final entry in item.entries)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: Text(
                            '${_formatLabel(entry.key.toString())}: '
                            '${_formatValue(entry.value)}',
                          ),
                        ),
                    ],
                  ),
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Text('• ${_formatValue(item)}'),
              ),
          ],
        ],
      );
    }

    // --------------------------------------------------------
    // MAP
    // --------------------------------------------------------

    if (value is Map) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final entry in value.entries)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _formatLabel(entry.key.toString()),
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 4),
                  Text(_formatValue(entry.value)),
                ],
              ),
            ),
        ],
      );
    }

    // --------------------------------------------------------
    // NILAI BIASA
    // --------------------------------------------------------

    return Text(_formatValue(value));
  }

  // ==========================================================
  // SHOW DETAIL
  // ==========================================================

  void _showDetails(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Row(
            children: [
              Icon(_getIcon(), color: _getColor()),
              const SizedBox(width: 10),
              Expanded(child: Text(title)),
            ],
          ),

          content: SizedBox(
            width: 650,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ------------------------------------------------
                  // MESSAGE LENGKAP
                  // ------------------------------------------------

                  Text(_displayMessage(), style: const TextStyle(fontSize: 16)),

                  // ------------------------------------------------
                  // DETAIL
                  // ------------------------------------------------
                  if (_hasDetails) ...[
                    const SizedBox(height: 20),

                    const Divider(),

                    const SizedBox(height: 10),

                    const Text(
                      'Detail',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 12),

                    _buildDetailsContent(details),
                  ],
                ],
              ),
            ),
          ),

          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
              },
              child: const Text('Tutup'),
            ),
          ],
        );
      },
    );
  }

  // ==========================================================
  // CARD
  // ==========================================================

  @override
  Widget build(BuildContext context) {
    final color = _getColor();

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: InkWell(
        onTap: () => _showDetails(context),
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
          child: Row(
            children: [
              Icon(_getIcon(), color: color, size: 32),

              const SizedBox(width: 15),

              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 5),

                    Text(
                      summary,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey.shade700,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(width: 12),

              Column(
                children: [
                  Text(
                    status,
                    style: TextStyle(color: color, fontWeight: FontWeight.bold),
                  ),

                  const SizedBox(height: 3),

                  Icon(
                    Icons.chevron_right,
                    color: Colors.grey.shade500,
                    size: 20,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
