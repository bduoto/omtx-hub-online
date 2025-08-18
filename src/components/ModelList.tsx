
import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Bookmark } from 'lucide-react';

interface Model {
  title: string;
  description: string;
  author: string;
  category: string;
  bookmarked: boolean;
}

interface ModelListProps {
  models: Model[];
}

export const ModelList: React.FC<ModelListProps> = ({ models }) => {
  return (
    <div className="space-y-4">
      {models.map((model, index) => (
        <div 
          key={index} 
          className="bg-gray-800 border border-gray-700 rounded-lg p-6 hover:bg-gray-750 hover:border-[#E2E756]/50 transition-all duration-200 cursor-pointer"
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-start justify-between mb-3">
                <h3 className="text-xl font-semibold text-white hover:text-[#E2E756] transition-colors">
                  {model.title}
                </h3>
                <button className="text-gray-500 hover:text-[#E2E756] transition-colors p-1">
                  <Bookmark className="w-5 h-5" />
                </button>
              </div>
              
              <p className="text-gray-300 text-sm leading-relaxed mb-3">
                {model.description}
              </p>
              
              <div className="flex items-center gap-4 mb-4">
                <p className="text-xs text-gray-400 italic">
                  {model.author}
                </p>
                <Badge variant="secondary" className="bg-gray-700 text-gray-200 hover:bg-gray-600">
                  {model.category}
                </Badge>
              </div>
              
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="text-xs font-montserrat font-medium bg-transparent border-[#E2E756] text-[#E2E756] hover:bg-[#E2E756] hover:text-gray-900 transition-colors"
                >
                  Paper
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="text-xs font-montserrat font-medium bg-transparent border-[#E2E756] text-[#E2E756] hover:bg-[#E2E756] hover:text-gray-900 transition-colors"
                >
                  Code
                </Button>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
