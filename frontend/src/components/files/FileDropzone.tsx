'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import { cn, formatBytes } from '@/lib/utils';
import { uploadFile } from '@/lib/api';

interface FileItem {
  file: File;
  status: 'pending' | 'uploading' | 'done' | 'error';
  fileId?: string;
  error?: string;
}

interface Props {
  caseId?: string;
  onUploaded?: (fileId: string, filename: string) => void;
}

const ACCEPTED = {
  'application/pdf': ['.pdf'],
  'image/vnd.dxf': ['.dxf'],
  'application/octet-stream': ['.dxf', '.step', '.stp', '.iges', '.igs', '.stl'],
};

export function FileDropzone({ caseId, onUploaded }: Props) {
  const [files, setFiles] = useState<FileItem[]>([]);

  const uploadOne = useCallback(async (item: FileItem, idx: number) => {
    setFiles(prev => prev.map((f, i) => i === idx ? { ...f, status: 'uploading' } : f));
    try {
      const result = await uploadFile(item.file, caseId);
      setFiles(prev => prev.map((f, i) => i === idx ? { ...f, status: 'done', fileId: result.file_id } : f));
      onUploaded?.(result.file_id, item.file.name);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Błąd przesyłania';
      setFiles(prev => prev.map((f, i) => i === idx ? { ...f, status: 'error', error: msg } : f));
    }
  }, [caseId, onUploaded]);

  const onDrop = useCallback((accepted: File[]) => {
    const newItems: FileItem[] = accepted.map(f => ({ file: f, status: 'pending' }));
    setFiles(prev => {
      const combined = [...prev, ...newItems];
      // start uploads for new items
      newItems.forEach((item, i) => {
        const idx = prev.length + i;
        setTimeout(() => uploadOne({ ...item }, idx), 50);
      });
      return combined;
    });
  }, [uploadOne]);

  const remove = (idx: number) => setFiles(prev => prev.filter((_, i) => i !== idx));

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxSize: 100 * 1024 * 1024,
  });

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 transition-colors',
          isDragActive
            ? 'border-brand-400 bg-brand-50'
            : 'border-slate-300 bg-slate-50 hover:border-brand-400 hover:bg-brand-50'
        )}
      >
        <input {...getInputProps()} />
        <Upload className={cn('mb-3 h-8 w-8', isDragActive ? 'text-brand-500' : 'text-slate-400')} />
        <p className="text-sm font-medium text-slate-700">
          {isDragActive ? 'Upuść pliki tutaj…' : 'Przeciągnij pliki lub kliknij, aby wybrać'}
        </p>
        <p className="mt-1 text-xs text-slate-400">PDF, DXF, STEP, IGES, STL — maks. 100 MB</p>
      </div>

      {files.length > 0 && (
        <ul className="space-y-2">
          {files.map((item, idx) => (
            <li key={idx} className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2">
              <File className="h-4 w-4 flex-shrink-0 text-slate-400" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-700">{item.file.name}</p>
                <p className="text-xs text-slate-400">{formatBytes(item.file.size)}</p>
              </div>
              <div className="flex-shrink-0">
                {item.status === 'uploading' && <Loader2 className="h-4 w-4 animate-spin text-brand-500" />}
                {item.status === 'done'      && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                {item.status === 'error'     && (
                  <div className="flex items-center gap-1">
                    <AlertCircle className="h-4 w-4 text-red-500" />
                    <span className="text-xs text-red-600">{item.error}</span>
                  </div>
                )}
                {item.status === 'pending'   && (
                  <button onClick={() => remove(idx)} className="text-slate-400 hover:text-slate-600">
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
