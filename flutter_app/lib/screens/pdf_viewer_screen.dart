import 'package:flutter/material.dart';
import 'package:pdfrx/pdfrx.dart';

/// Pratinjau PDF lokal dengan highlight lokasi ukuran font yang tidak sesuai.
///
/// Koordinat bbox berasal dari PyMuPDF dalam satuan point (72 point per inci).
/// Skala overlay dihitung dari ukuran halaman yang ditampilkan oleh pdfrx.
class PdfViewerScreen extends StatelessWidget {
  final String pdfPath;
  final List<Map<String, dynamic>> highlightLocations;

  const PdfViewerScreen({
    super.key,
    required this.pdfPath,
    this.highlightLocations = const <Map<String, dynamic>>[],
  });

  String get _fileName => pdfPath.split(RegExp(r'[\\/]')).last;

  int? _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '');
  }

  double? _toDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '');
  }

  List<Widget> _buildPageHighlights(
    BuildContext context,
    Rect pageRect,
    PdfPage page,
  ) {
    if (page.width <= 0 || page.height <= 0) return const <Widget>[];

    // pageRect adalah ukuran halaman yang sudah ditampilkan/di-zoom.
    // Rasio ini juga memperhitungkan skala awal saat halaman di-fit ke viewer.
    final scaleX = pageRect.width / page.width;
    final scaleY = pageRect.height / page.height;
    final overlays = <Widget>[];

    for (final location in highlightLocations) {
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

      overlays.add(
        Positioned(
          left: x0 * scaleX,
          top: y0 * scaleY,
          width: width,
          height: height,
          child: IgnorePointer(
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: Colors.red.withValues(alpha: 0.22),
                border: Border.all(
                  color: Colors.red.withValues(alpha: 0.75),
                  width: 0.7,
                ),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
        ),
      );
    }

    return overlays;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_fileName, overflow: TextOverflow.ellipsis),
      ),
      body: Column(
        children: [
          if (highlightLocations.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              color: Colors.red.withValues(alpha: 0.08),
              child: Row(
                children: [
                  Container(
                    width: 16,
                    height: 16,
                    decoration: BoxDecoration(
                      color: Colors.red.withValues(alpha: 0.22),
                      border: Border.all(color: Colors.red, width: 0.8),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${highlightLocations.length} lokasi ukuran font ditandai merah.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                ],
              ),
            ),
          Expanded(
            child: PdfViewer.file(
              pdfPath,
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
