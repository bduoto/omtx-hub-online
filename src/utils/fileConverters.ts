// Removed Miew import - now using Mol* for 3D visualization



/**
 * Download a file with given content and filename
 * @param content - File content as string
 * @param filename - Name of the file to download
 * @param mimeType - MIME type of the file
 */
export const downloadFile = (
  content: string, 
  filename: string, 
  mimeType: string = 'text/plain'
): void => {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

/**
 * Download CIF file
 * @param cifContent - CIF content as string
 * @param filename - Optional filename (defaults to structure.cif)
 */
export const downloadCifFile = (cifContent: string, filename: string = 'structure.cif'): void => {
  downloadFile(cifContent, filename, 'chemical/x-cif');
};



/**
 * Extract CIF content from prediction result
 * @param result - Prediction result object
 * @returns CIF content as string or null if not available
 */
export const extractCifContent = (result: any): string | null => {
  if (!result) return null;
  
  // Try different sources for CIF content
  const cifContent = result.structure_file_content ||
    (result.structure_file_base64 ? atob(result.structure_file_base64) : null) ||
    result.structure_files?.primary_structure?.content ||
    (result.structure_files?.primary_structure?.base64 ? 
      atob(result.structure_files.primary_structure.base64) : null);
  
  return cifContent || null;
};

/**
 * Validate structure file content
 * @param content - Structure file content
 * @param format - Expected format ('cif' or 'pdb')
 * @returns boolean indicating if content is valid
 */
export const validateStructureContent = (content: string, format: 'cif' | 'pdb'): boolean => {
  if (!content || typeof content !== 'string') return false;
  
  const trimmedContent = content.trim();
  if (trimmedContent.length === 0) return false;
  
  switch (format) {
    case 'cif':
      // Basic CIF validation - should contain data blocks
      return /^data_/.test(trimmedContent) || trimmedContent.includes('data_');
    
    case 'pdb':
      // Basic PDB validation - should contain HEADER or ATOM records
      return /^(HEADER|ATOM|HETATM)/.test(trimmedContent) || 
             trimmedContent.includes('HEADER') || 
             trimmedContent.includes('ATOM');
    
    default:
      return false;
  }
};

/**
 * Get file size in human-readable format
 * @param content - File content as string
 * @returns Human-readable file size
 */
export const getFileSizeString = (content: string): string => {
  const bytes = new Blob([content]).size;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  
  if (bytes === 0) return '0 B';
  
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
};

/**
 * Generate filename with timestamp
 * @param baseName - Base name for the file
 * @param extension - File extension
 * @returns Filename with timestamp
 */
export const generateTimestampedFilename = (baseName: string, extension: string): string => {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  return `${baseName}-${timestamp}.${extension}`;
}; 