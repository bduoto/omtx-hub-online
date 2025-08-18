
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Bookmark } from 'lucide-react';

interface ModelCardProps {
  title: string;
  description: string;
  author: string;
  category: string;
  bookmarked: boolean;
}

export const ModelCard: React.FC<ModelCardProps> = ({
  title,
  description,
  author,
  category,
  bookmarked: initialBookmarked
}) => {
  const [isBookmarked, setIsBookmarked] = useState(false);

  const handleBookmarkClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsBookmarked(!isBookmarked);
  };

  const handleCardClick = () => {
    if (title === 'Boltz-2') {
      window.open('/boltz2', '_blank');
    } else if (title === 'RFantibody') {
      window.open('/rfantibody', '_blank');
    }
  };

  return (
    <Card 
      className="group hover:shadow-lg transition-all duration-200 cursor-pointer h-full flex flex-col bg-gray-800 border-gray-700 hover:bg-gray-750 hover:border-[#E2E756]/50 hover:scale-[1.02] relative"
      onClick={handleCardClick}
    >
      {/* Folded corner effect for hover */}
      <div className="absolute top-0 right-0 w-0 h-0 border-l-[20px] border-l-transparent border-t-[20px] border-t-[#E2E756] rounded-tr-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200"></div>
      
      <CardHeader className="pb-3 flex-none">
        <div className="flex items-start justify-between">
          <CardTitle className="text-lg font-semibold text-white group-hover:text-[#E2E756] transition-colors">
            {title}
          </CardTitle>
          <button 
            onClick={handleBookmarkClick}
            className={`p-1 rounded transition-colors ${
              isBookmarked 
                ? 'text-[#E2E756]' 
                : 'text-gray-500 hover:text-[#E2E756]'
            }`}
          >
            <Bookmark 
              className="w-5 h-5" 
              fill={isBookmarked ? 'currentColor' : 'none'}
            />
          </button>
        </div>
      </CardHeader>
      
      <CardContent className="flex-1 flex flex-col justify-between">
        <div className="space-y-3">
          <p className="text-gray-300 text-sm leading-relaxed flex-1">
            {description}
          </p>
          <p className="text-xs text-gray-400 italic">
            {author}
          </p>
          <Badge variant="secondary" className="w-fit bg-gray-700 text-gray-200 hover:bg-gray-600">
            {category}
          </Badge>
        </div>
        
        <div className="flex gap-2 mt-4 pt-4 border-t border-gray-700">
          <Button 
            variant="outline" 
            size="sm" 
            className="flex-1 text-xs font-montserrat font-medium bg-transparent border-[#E2E756] text-[#E2E756] hover:bg-[#E2E756] hover:text-gray-900 transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            Paper
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            className="flex-1 text-xs font-montserrat font-medium bg-transparent border-[#E2E756] text-[#E2E756] hover:bg-[#E2E756] hover:text-gray-900 transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            Code
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
