
import React, { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { 
  Play, 
  Pause, 
  SkipBack, 
  SkipForward, 
  RotateCcw, 
  Clock,
  Film
} from 'lucide-react';

interface TimelinePanelProps {
  isPlaying: boolean;
  onPlayToggle: (playing: boolean) => void;
  molecule: any;
}

export const TimelinePanel: React.FC<TimelinePanelProps> = ({
  isPlaying,
  onPlayToggle,
  molecule
}) => {
  const [currentFrame, setCurrentFrame] = useState([0]);
  const [playbackSpeed, setPlaybackSpeed] = useState([1]);
  const totalFrames = 100; // Mock value

  const formatTime = (frame: number) => {
    const seconds = (frame * 0.1).toFixed(1);
    return `${seconds}s`;
  };

  return (
    <div className="h-24 bg-gray-800 border-t border-gray-700 flex items-center px-4">
      <Card className="w-full bg-gray-700 border-gray-600">
        <CardContent className="p-3">
          <div className="flex items-center space-x-4">
            {/* Playback Controls */}
            <div className="flex items-center space-x-2">
              <Button
                size="sm"
                variant="ghost"
                className="w-8 h-8 p-0 text-gray-400 hover:text-white"
                onClick={() => setCurrentFrame([0])}
              >
                <SkipBack className="w-4 h-4" />
              </Button>
              
              <Button
                size="sm"
                className="w-8 h-8 p-0 text-black"
                style={{ backgroundColor: isPlaying ? '#E7569A' : '#56E7A4' }}
                onClick={() => onPlayToggle(!isPlaying)}
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </Button>
              
              <Button
                size="sm"
                variant="ghost"
                className="w-8 h-8 p-0 text-gray-400 hover:text-white"
                onClick={() => setCurrentFrame([totalFrames - 1])}
              >
                <SkipForward className="w-4 h-4" />
              </Button>
              
              <Button
                size="sm"
                variant="ghost"
                className="w-8 h-8 p-0 text-gray-400 hover:text-white"
              >
                <RotateCcw className="w-4 h-4" />
              </Button>
            </div>

            {/* Timeline Slider */}
            <div className="flex-1 mx-4">
              <div className="flex items-center space-x-3">
                <div className="flex items-center text-xs text-gray-400">
                  <Clock className="w-3 h-3 mr-1" />
                  {formatTime(currentFrame[0])}
                </div>
                
                <div className="flex-1">
                  <Slider
                    value={currentFrame}
                    onValueChange={setCurrentFrame}
                    max={totalFrames - 1}
                    step={1}
                    className="w-full"
                    disabled={!molecule}
                  />
                </div>
                
                <div className="text-xs text-gray-400">
                  {formatTime(totalFrames - 1)}
                </div>
              </div>
              
              <div className="flex justify-between items-center mt-1">
                <span className="text-xs text-gray-500">
                  Frame {currentFrame[0] + 1} / {totalFrames}
                </span>
                <div className="flex items-center space-x-2">
                  <Film className="w-3 h-3 text-gray-500" />
                  <span className="text-xs text-gray-500">Speed:</span>
                  <div className="w-16">
                    <Slider
                      value={playbackSpeed}
                      onValueChange={setPlaybackSpeed}
                      min={0.1}
                      max={3}
                      step={0.1}
                      className="w-full"
                    />
                  </div>
                  <span className="text-xs text-gray-400 w-8">
                    {playbackSpeed[0].toFixed(1)}x
                  </span>
                </div>
              </div>
            </div>

            {/* Status */}
            <div className="text-right">
              <div className="text-xs text-gray-400">
                {molecule ? 'Trajectory loaded' : 'No trajectory'}
              </div>
              <div className="text-xs" style={{ color: isPlaying ? '#56E7A4' : '#E7569A' }}>
                {isPlaying ? 'Playing' : 'Paused'}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
