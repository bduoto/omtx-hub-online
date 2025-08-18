
import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Upload, File, X, Plus } from 'lucide-react';

interface FileUploadDialogProps {
  children: React.ReactNode;
}

export const FileUploadDialog = ({ children }: FileUploadDialogProps) => {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const newFiles = Array.from(e.dataTransfer.files);
      setUploadedFiles(prev => [...prev, ...newFiles]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const newFiles = Array.from(e.target.files);
      setUploadedFiles(prev => [...prev, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden bg-gray-800 border-gray-700 text-white">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold text-white">
            Upload Files
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6 overflow-y-auto pr-2">
          {/* Upload Area */}
          <Card className="bg-gray-700 border-gray-600">
            <CardContent className="p-6">
              <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                  dragActive 
                    ? 'border-blue-400 bg-blue-900/20' 
                    : 'border-gray-500 hover:border-gray-400'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">
                  Drop files here or click to upload
                </h3>
                <p className="text-gray-400 mb-4">
                  Support for protein sequences, structures, and analysis files
                </p>
                <input
                  type="file"
                  multiple
                  onChange={handleFileInput}
                  className="hidden"
                  id="file-upload"
                  accept=".pdb,.fasta,.txt,.csv,.json"
                />
                <label htmlFor="file-upload">
                  <Button 
                    className="bg-[#E2E756] hover:bg-[#d4d347] text-black font-medium border-0"
                    asChild
                  >
                    <span className="cursor-pointer">
                      <Plus className="w-4 h-4 mr-2" />
                      Choose Files
                    </span>
                  </Button>
                </label>
              </div>
            </CardContent>
          </Card>

          {/* File List */}
          {uploadedFiles.length > 0 && (
            <Card className="bg-gray-700 border-gray-600">
              <CardContent className="p-6">
                <h3 className="text-lg font-medium text-white mb-4">
                  Uploaded Files ({uploadedFiles.length})
                </h3>
                <div className="space-y-3">
                  {uploadedFiles.map((file, index) => (
                    <div 
                      key={index}
                      className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-600"
                    >
                      <div className="flex items-center space-x-3">
                        <File className="h-5 w-5 text-blue-400" />
                        <div>
                          <p className="text-white font-medium">{file.name}</p>
                          <p className="text-gray-400 text-sm">
                            {formatFileSize(file.size)} • {file.type || 'Unknown type'}
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                        className="text-gray-400 hover:text-red-400 hover:bg-red-900/20"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* File Type Info */}
          <Card className="bg-gray-700 border-gray-600">
            <CardContent className="p-6">
              <h3 className="text-lg font-medium text-white mb-4">
                Supported File Types
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <h4 className="text-blue-400 font-medium mb-2">Protein Sequences</h4>
                  <ul className="text-gray-300 space-y-1">
                    <li>• FASTA (.fasta, .fa)</li>
                    <li>• Text files (.txt)</li>
                    <li>• GenBank (.gb)</li>
                  </ul>
                </div>
                <div>
                  <h4 className="text-blue-400 font-medium mb-2">Structure Files</h4>
                  <ul className="text-gray-300 space-y-1">
                    <li>• PDB (.pdb)</li>
                    <li>• mmCIF (.cif)</li>
                    <li>• MOL2 (.mol2)</li>
                  </ul>
                </div>
                <div>
                  <h4 className="text-blue-400 font-medium mb-2">Data Files</h4>
                  <ul className="text-gray-300 space-y-1">
                    <li>• CSV (.csv)</li>
                    <li>• JSON (.json)</li>
                    <li>• Excel (.xlsx)</li>
                  </ul>
                </div>
                <div>
                  <h4 className="text-blue-400 font-medium mb-2">Analysis Files</h4>
                  <ul className="text-gray-300 space-y-1">
                    <li>• Log files (.log)</li>
                    <li>• Output files (.out)</li>
                    <li>• Custom formats</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-600">
            <Button variant="outline" className="text-gray-300 border-gray-600 hover:bg-gray-700">
              Cancel
            </Button>
            <Button 
              className="bg-[#E2E756] hover:bg-[#d4d347] text-black font-medium border-0"
              disabled={uploadedFiles.length === 0}
            >
              Upload {uploadedFiles.length > 0 ? `${uploadedFiles.length} file${uploadedFiles.length > 1 ? 's' : ''}` : 'Files'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
