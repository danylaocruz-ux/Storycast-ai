import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:file_picker/file_picker.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/book_model.dart';
import '../../../data/services/api_service.dart';
import '../../library/providers/library_provider.dart';

class UploadScreen extends ConsumerStatefulWidget {
  const UploadScreen({super.key});

  @override
  ConsumerState<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends ConsumerState<UploadScreen> {
  PlatformFile? _selectedFile;
  bool _isUploading = false;
  String? _error;

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'epub', 'docx', 'txt'],
      allowMultiple: false,
    );
    if (result != null && result.files.isNotEmpty) {
      setState(() {
        _selectedFile = result.files.first;
        _error = null;
      });
    }
  }

  Future<void> _upload() async {
    if (_selectedFile == null || _selectedFile!.path == null) return;

    setState(() {
      _isUploading = true;
      _error = null;
    });

    try {
      final data = await ApiService.instance.uploadBook(
        _selectedFile!.path!,
        _selectedFile!.name,
      );
      final book = BookModel.fromJson(data);
      ref.read(libraryProvider.notifier).addBook(book);

      if (mounted) {
        context.go('/processing/${book.id}');
      }
    } catch (e) {
      setState(() {
        _isUploading = false;
        _error = 'Falha no upload: ${e.toString()}';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Adicionar livro'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.go('/home'),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Formatos suportados',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 12),
            // Chips de formato
            Wrap(
              spacing: 8,
              children: ['PDF', 'EPUB', 'DOCX', 'TXT'].map((fmt) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.primary.withOpacity(0.3)),
                ),
                child: Text(
                  fmt,
                  style: const TextStyle(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                ),
              )).toList(),
            ),

            const SizedBox(height: 32),

            // Drop zone
            GestureDetector(
              onTap: _isUploading ? null : _pickFile,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 48),
                decoration: BoxDecoration(
                  color: _selectedFile != null
                      ? AppColors.primary.withOpacity(0.08)
                      : AppColors.surfaceVariant,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: _selectedFile != null ? AppColors.primary : AppColors.border,
                    width: _selectedFile != null ? 2 : 1,
                  ),
                ),
                child: Column(
                  children: [
                    Icon(
                      _selectedFile != null ? Icons.check_circle : Icons.upload_file,
                      color: _selectedFile != null ? AppColors.primary : AppColors.textHint,
                      size: 56,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      _selectedFile != null
                          ? _selectedFile!.name
                          : 'Toque para selecionar arquivo',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: _selectedFile != null
                            ? AppColors.textPrimary
                            : AppColors.textSecondary,
                        fontWeight: _selectedFile != null ? FontWeight.w600 : FontWeight.normal,
                        fontSize: 15,
                      ),
                    ),
                    if (_selectedFile != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        _formatSize(_selectedFile!.size),
                        style: const TextStyle(
                          color: AppColors.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),

            if (_error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.error.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: AppColors.error, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _error!,
                        style: const TextStyle(color: AppColors.error, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            const Spacer(),

            // Info box
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.info.withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Icon(Icons.info_outline, color: AppColors.info, size: 18),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Após o upload, a IA analisará o texto, identificará personagens e gerará o áudio automaticamente. O processo pode levar alguns minutos.',
                      style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: (_selectedFile == null || _isUploading) ? null : _upload,
                child: _isUploading
                    ? const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          ),
                          SizedBox(width: 10),
                          Text('Enviando...'),
                        ],
                      )
                    : const Text('Processar livro'),
              ),
            ),

            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  String _formatSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
}
                  