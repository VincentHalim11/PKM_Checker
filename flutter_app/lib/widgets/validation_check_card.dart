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

  // ==========================================================
  // BUILD DETAIL CONTENT
  // ==========================================================

  Widget _buildDetailsContent(dynamic value) {
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

                  Text(message, style: const TextStyle(fontSize: 16)),

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
