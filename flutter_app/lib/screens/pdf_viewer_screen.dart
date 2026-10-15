import 'dart:io';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:pdfrx/pdfrx.dart';

import '../services/validator_service.dart';

/// Pratinjau PDF dengan highlight ukuran font (merah) dan jenis font (biru).
///
/// Klik label jumlah temuan di bagian atas untuk membuka daftar temuan.
/// Pilih salah satu temuan untuk berpindah ke halaman PDF terkait tanpa zoom ke kotak teks.
class PdfViewerScreen extends StatefulWidget {
  final String pdfPath;
  final List<Map<String, dynamic>> highlightLocations;
  final List<Map<String, dynamic>> fontHighlightLocations;
  final List<Map<String, dynamic>> marginHighlightLocations;

  const PdfViewerScreen({
    super.key,
    required this.pdfPath,
    this.highlightLocations = const <Map<String, dynamic>>[],
    this.fontHighlightLocations = const <Map<String, dynamic>>[],
    this.marginHighlightLocations = const <Map<String, dynamic>>[],
  });

  @override
  State<PdfViewerScreen> createState() => _PdfViewerScreenState();
}

class _PdfViewerScreenState extends State<PdfViewerScreen> {
  final PdfViewerController _controller = PdfViewerController();
  String? _selectedLocationKey;
  bool _isExporting = false;

  int? _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '');
  }

  double? _toDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '');
  }

  String _locationKey(Map<String, dynamic> location, String category) {
    return '$category|${location['page']}|${location['bbox']}|${location['text']}';
  }

  List<Widget> _buildPageHighlights(
    BuildContext context,
    Rect pageRect,
    PdfPage page,
  ) {
    if (page.width <= 0 || page.height <= 0) return const <Widget>[];

    final scaleX = pageRect.width / page.width;
    final scaleY = pageRect.height / page.height;
    final overlays = <Widget>[];

    void addHighlights(
      List<Map<String, dynamic>> locations,
      Color color,
      String category,
    ) {
      for (final location in locations) {
        if (_toInt(location['page']) != page.pageNumber) continue;

        final bbox = location['bbox'];
        if (bbox is! List || bbox.length < 4) continue;

        final x0 = _toDouble(bbox[0]);
        final y0 = _toDouble(bbox[1]);
        final x1 = _toDouble(bbox[2]);
        final y1 = _toDouble(bbox[3]);
        if (x0 == null || y0 == null || x1 == null || y1 == null) continue;

        final width = (x1 - x0) * scaleX;
        final height = (y1 - y0) * scaleY;
        if (!width.isFinite || !height.isFinite || width <= 0 || height <= 0) {
          continue;
        }

        final isSelected =
            _selectedLocationKey == _locationKey(location, category);

        overlays.add(
          Positioned(
            left: x0 * scaleX,
            top: y0 * scaleY,
            width: width,
            height: height,
            child: IgnorePointer(
              // Interaksi dilakukan melalui daftar temuan, supaya gesture
              // scroll/zoom pada PDF tidak terganggu oleh overlay.
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: color.withValues(alpha: isSelected ? 0.34 : 0.22),
                  border: Border.all(
                    color: isSelected? color: color.withValues(alpha: 0.80),
                    width: isSelected ? 2.0 : 0.8,
                  ),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ),
        );
      }
    }

    addHighlights(widget.highlightLocations, Colors.red, 'font_size');
    addHighlights(widget.fontHighlightLocations, Colors.blue, 'font');
    addHighlights(widget.marginHighlightLocations, Colors.deepPurple, 'margin');

    return overlays;
  }

  Widget _buildLegendButton({
    required Color color,
    required String label,
    required int count,
    required VoidCallback? onPressed,
  }) {
    return TextButton(
      onPressed: onPressed,
      style: TextButton.styleFrom(
        foregroundColor: Colors.black87,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        visualDensity: VisualDensity.compact,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 16,
            height: 16,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.22),
              border: Border.all(color: color, width: 1),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 8),
          Text('$count lokasi $label'),
          if (count > 0) ...[
            const SizedBox(width: 4),
            const Icon(Icons.list_alt, size: 16),
          ],
        ],
      ),
    );
  }

  String _locationDescription(
    Map<String, dynamic> location, {
    required String category,
  }) {
    final page = _toInt(location['page']) ?? '?';

    if (category == 'font') {
      final font = location['font']?.toString() ?? 'Font tidak diketahui';
      return 'Halaman $page · Font terdeteksi: $font';
    }

    if (category == 'margin') {
      final sideCode = location['type']?.toString() ?? '';
      const sideLabels = {
        'LEFT': 'kiri',
        'RIGHT': 'kanan',
        'TOP': 'atas',
        'BOTTOM': 'bawah',
      };
      final side = sideLabels[sideCode] ?? sideCode;
      final position = _toDouble(location['position_cm']);
      final expected = _toDouble(location['expected_cm']);
      if (position != null && expected != null) {
        return 'Halaman $page · Sisi $side · Posisi ${position.toStringAsFixed(2)} cm · Target ${expected.toStringAsFixed(2)} cm';
      }
      return 'Halaman $page · Sisi margin $side';
    }

    final size = location['size'];
    final expected = location['expected_sizes'];
    final expectedText = expected is List
        ? expected.map((value) => '$value').join(' / ')
        : null;
    if (size != null && expectedText != null && expectedText.isNotEmpty) {
      return 'Halaman $page · Terdeteksi $size pt · Seharusnya $expectedText pt';
    }
    if (size != null) return 'Halaman $page · Terdeteksi $size pt';
    return 'Halaman $page';
  }

  Future<void> _showFindings({required String category}) async {
    final List<Map<String, dynamic>> locations;
    final String title;
    final Color color;

    switch (category) {
      case 'font_size':
        locations = widget.highlightLocations;
        title = 'Temuan ukuran font';
        color = Colors.red;
        break;
      case 'font':
        locations = widget.fontHighlightLocations;
        title = 'Temuan jenis font';
        color = Colors.blue;
        break;
      case 'margin':
        locations = widget.marginHighlightLocations;
        title = 'Temuan margin';
        color = Colors.deepPurple;
        break;
      default:
        return;
    }

    if (locations.isEmpty) return;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: DraggableScrollableSheet(
            expand: false,
            initialChildSize: 0.70,
            minChildSize: 0.40,
            maxChildSize: 0.92,
            builder: (context, scrollController) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(20, 4, 20, 4),
                    child: Text(
                      title,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                  ),
                  const Padding(
                    padding: EdgeInsets.fromLTRB(20, 0, 20, 10),
                    child: Text('Pilih temuan untuk menuju halaman terkait di PDF.'),
                  ),
                  const Divider(height: 1),
                  Expanded(
                    child: ListView.separated(
                      controller: scrollController,
                      itemCount: locations.length,
                      separatorBuilder: (_, _) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final location = locations[index];
                        final text = location['text']?.toString().trim();
                        final key = _locationKey(location, category);
                        final description = _locationDescription(
                          location,
                          category: category,
                        );

                        return ListTile(
                          leading: Container(
                            width: 12,
                            height: 40,
                            decoration: BoxDecoration(
                              color: color.withValues(alpha: 0.22),
                              border: Border.all(color: color,width: 1.3),
                              borderRadius: BorderRadius.circular(3),
                            ),
                          ),
                          title: Text(
                            (text == null || text.isEmpty)
                                ? '(Teks tidak tersedia)'
                                : text,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text(description),
                          trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                          onTap: () async {
                            Navigator.of(sheetContext).pop();
                            await _jumpToLocation(location, key: key);
                          },
                        );
                      },
                    ),
                  ),
                ],
              );
            },
          ),
        );
      },
    );
  }

  Future<void> _jumpToLocation(
    Map<String, dynamic> location, {
    required String key,
  }) async {
    final pageNumber = _toInt(location['page']);
    if (pageNumber == null) return;

    if (!_controller.isReady ||
        pageNumber < 1 ||
        pageNumber > _controller.pageCount) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('PDF masih dimuat. Coba lagi sebentar.')),
        );
      }
      return;
    }

    // Pilih highlight, tetapi navigasi hanya ke halaman terkait.
    // Jangan memakai goToRectInsidePage karena itu akan memperbesar area bbox.
    setState(() => _selectedLocationKey = key);
    await _controller.goToPage(
      pageNumber: pageNumber,
      anchor: PdfPageAnchor.all,
    );
  }


  Future<void> _exportHighlightedPdf() async {
    if (_isExporting) return;

    FileSaveLocation? location;

    // Buka dialog untuk memilih lokasi dan nama file.
    try {
      location = await getSaveLocation(
        suggestedName: widget.pdfPath
            .split(RegExp(r'[\\/]'))
            .last
            .replaceFirst(
              RegExp(r'\.pdf$', caseSensitive: false),
              '_highlighted.pdf',
            ),
        acceptedTypeGroups: const [
          XTypeGroup(
            label: 'PDF',
            extensions: ['pdf'],
          ),
        ],
        confirmButtonText: 'Simpan',
      );
    } catch (error) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Gagal membuka dialog penyimpanan: $error')),
      );
      return;
    }

    // Pengguna membatalkan dialog.
    if (location == null || !mounted) return;

    var outputPath = location.path;

    // Pastikan nama hasil ekspor memiliki ekstensi PDF.
    if (!outputPath.toLowerCase().endsWith('.pdf')) {
      outputPath = '$outputPath.pdf';
    }

    String normalisePath(String path) {
      final absolutePath = File(path).absolute.path;
      return Platform.isWindows
          ? absolutePath.toLowerCase()
          : absolutePath;
    }

    // Jangan sampai PDF asli tertimpa.
    if (normalisePath(outputPath) == normalisePath(widget.pdfPath)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Pilih nama atau lokasi lain agar PDF asli tidak tertimpa.',
          ),
        ),
      );
      return;
    }

    setState(() => _isExporting = true);

    try {
      final bytes = await ValidatorService.exportHighlightedPdf(
        pdfPath: widget.pdfPath,
        fontSizeLocations: widget.highlightLocations,
        fontLocations: widget.fontHighlightLocations,
        marginLocations: widget.marginHighlightLocations,
      );

      await File(outputPath).writeAsBytes(bytes, flush: true);

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'PDF dengan highlight dan legenda berhasil disimpan:\n$outputPath',
          ),
          duration: const Duration(seconds: 6),
        ),
      );
    } catch (error) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Gagal mengekspor PDF: $error')),
      );
    } finally {
      if (mounted) {
        setState(() => _isExporting = false);
      }
    }
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(

      appBar: AppBar(
        title: Text(
          widget.pdfPath.split(RegExp(r'[\\/]')).last,
          overflow: TextOverflow.ellipsis,
        ),
        actions: [
          IconButton(
            tooltip: 'Unduh PDF dengan highlight dan legenda',
            onPressed: _isExporting ? null : _exportHighlightedPdf,
            icon: _isExporting
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.download_rounded),
          ),
        ],
      ),
      body: Column(
        children: [
          if (widget.highlightLocations.isNotEmpty ||
              widget.fontHighlightLocations.isNotEmpty ||
              widget.marginHighlightLocations.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              color: Colors.grey.withValues(alpha: 0.06),
              child: Wrap(
                spacing: 8,
                runSpacing: 2,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  _buildLegendButton(
                    color: Colors.red,
                    label: 'ukuran font',
                    count: widget.highlightLocations.length,
                    onPressed: widget.highlightLocations.isEmpty
                        ? null
                        : () => _showFindings(category: 'font_size'),
                  ),
                  _buildLegendButton(
                    color: Colors.blue,
                    label: 'jenis font',
                    count: widget.fontHighlightLocations.length,
                    onPressed: widget.fontHighlightLocations.isEmpty
                        ? null
                        : () => _showFindings(category: 'font'),
                  ),
                  _buildLegendButton(
                    color: Colors.deepPurple,
                    label: 'margin',
                    count: widget.marginHighlightLocations.length,
                    onPressed: widget.marginHighlightLocations.isEmpty
                        ? null
                        : () => _showFindings(category: 'margin'),
                  ),
                ],
              ),
            ),
          Expanded(
            child: PdfViewer.file(
              widget.pdfPath,
              controller: _controller,
              params: PdfViewerParams(
                pageOverlaysBuilder: _buildPageHighlights,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
