/**
 * Utility functions for Boltz-2 metric formatting and color coding
 * Based on the Boltz-2 paper specifications
 */

// Metric direction indicators (better direction)
export const METRIC_DIRECTIONS = {
  // Direct Binding Outputs
  affinity: 'negative', // More negative = better (tighter binding)
  affinity_probability: 'positive', // Higher = better
  
  // Ensemble Support
  ensemble_affinity: 'negative', // More negative = better
  ensemble_probability: 'positive', // Higher = better
  ensemble_affinity_1: 'negative',
  ensemble_probability_1: 'positive',
  ensemble_affinity_2: 'negative',
  ensemble_probability_2: 'positive',
  
  // Model-Level Reliability
  confidence: 'positive', // Higher = better
  
  // Interface-Specific Structure Confidence
  iptm: 'positive', // Higher = better
  ligand_iptm: 'positive', // Higher = better
  complex_iplddt: 'positive', // Higher = better
  complex_ipde: 'negative', // Lower = better (distance error)
  
  // Global/Monomer Structure Confidence
  complex_plddt: 'positive', // Higher = better
  ptm: 'positive', // Higher = better
} as const;

// Color coding for affinity values (log scale with 1 µM reference)
export const getAffinityColor = (value: number | undefined | null): string => {
  if (value === undefined || value === null) return 'text-gray-400';
  
  // Affinity is on log scale referenced to 1 µM
  // More negative = stronger binding
  if (value <= -1) return 'text-green-400'; // Strong (≈ <0.1 µM)
  if (value <= 0) return 'text-yellow-400'; // Moderate (≈ 0.1–1 µM)
  if (value <= 1) return 'text-orange-400'; // Weak (≈ 1–10 µM)
  return 'text-red-400'; // Poor (≫ 10 µM)
};

// Get background color class for affinity
export const getAffinityBgColor = (value: number | undefined | null): string => {
  if (value === undefined || value === null) return 'bg-gray-900/50';
  
  if (value <= -1) return 'bg-green-900/20'; // Strong
  if (value <= 0) return 'bg-yellow-900/20'; // Moderate
  if (value <= 1) return 'bg-orange-900/20'; // Weak
  return 'bg-red-900/20'; // Poor
};

// Color coding for probability values (0-1 scale)
export const getProbabilityColor = (value: number | undefined | null): string => {
  if (value === undefined || value === null) return 'text-gray-400';
  
  if (value >= 0.7) return 'text-green-400'; // High
  if (value >= 0.4) return 'text-yellow-400'; // Medium
  return 'text-red-400'; // Low
};

// Color coding for confidence/iPTM values
export const getConfidenceColor = (value: number | undefined | null): string => {
  if (value === undefined || value === null) return 'text-gray-400';
  
  if (value >= 0.85) return 'text-green-400'; // Very strong
  if (value >= 0.70) return 'text-blue-400'; // Usable
  if (value >= 0.50) return 'text-yellow-400'; // Risky
  return 'text-red-400'; // Poor
};

// Color coding for pLDDT values
export const getPLDDTColor = (value: number | undefined | null): string => {
  if (value === undefined || value === null) return 'text-gray-400';
  
  if (value >= 90) return 'text-green-400'; // Great
  if (value >= 70) return 'text-blue-400'; // Good
  if (value >= 50) return 'text-yellow-400'; // Moderate
  return 'text-red-400'; // Poor
};

// Color coding for iPDE (Interface Predicted Distance Error)
export const getIPDEColor = (value: number | undefined | null): string => {
  if (value === undefined || value === null) return 'text-gray-400';
  
  // Lower is better for distance error
  if (value <= 1.0) return 'text-green-400'; // Strong
  if (value <= 2.0) return 'text-yellow-400'; // Okay
  return 'text-red-400'; // Weak
};

// Format affinity value with appropriate label
export const formatAffinityValue = (value: number | undefined | null): string => {
  if (value === undefined || value === null) return 'N/A';
  
  const formatted = value.toFixed(3);
  
  // Add approximate µM range based on log scale
  if (value <= -2) return `${formatted} (≈<0.01 µM)`;
  if (value <= -1) return `${formatted} (≈<0.1 µM)`;
  if (value <= 0) return `${formatted} (≈0.1-1 µM)`;
  if (value <= 1) return `${formatted} (≈1-10 µM)`;
  return `${formatted} (≈>10 µM)`;
};

// Get metric description
export const getMetricDescription = (metric: string): string => {
  const descriptions: Record<string, string> = {
    affinity: 'IC50-like binding strength (log scale, 1 µM ref). More negative = tighter binding',
    affinity_probability: 'Probability the ligand binds the protein (0-1)',
    ensemble_affinity: 'Calibrated ensemble affinity with MW correction. Preferred for ranking',
    ensemble_probability: 'Average binding likelihood across ensemble models',
    confidence: 'Overall confidence score (based on iPTM)',
    iptm: 'Interface pTM - protein-ligand interface quality',
    ligand_iptm: 'Ligand-specific interface pTM',
    complex_iplddt: 'Interface pLDDT - quality of contacting residues',
    complex_ipde: 'Interface Predicted Distance Error (Å). Lower = better',
    complex_plddt: 'pLDDT across full complex',
    ptm: 'Predicted TM-score for whole complex',
  };
  
  return descriptions[metric] || metric;
};

// Get metric unit
export const getMetricUnit = (metric: string): string => {
  const units: Record<string, string> = {
    affinity: 'log(µM)',
    affinity_probability: '',
    ensemble_affinity: 'log(µM)',
    ensemble_probability: '',
    complex_ipde: 'Å',
  };
  
  return units[metric] || '';
};

// Determine if a value is "good" based on metric type
export const isGoodValue = (metric: string, value: number | undefined | null): boolean => {
  if (value === undefined || value === null) return false;
  
  const direction = METRIC_DIRECTIONS[metric as keyof typeof METRIC_DIRECTIONS];
  
  if (direction === 'negative') {
    // For negative-better metrics (affinity)
    return value <= -0.5;
  } else if (direction === 'positive') {
    // For positive-better metrics
    if (metric.includes('probability')) {
      return value >= 0.5;
    }
    if (metric.includes('iptm') || metric.includes('ptm')) {
      return value >= 0.6;
    }
    if (metric.includes('plddt')) {
      return value >= 70;
    }
    if (metric === 'confidence') {
      return value >= 0.7;
    }
  } else if (metric === 'complex_ipde') {
    // Special case: lower is better
    return value <= 2.0;
  }
  
  return false;
};

// Get color based on metric type and value
export const getMetricColor = (metric: string, value: number | undefined | null): string => {
  if (value === undefined || value === null) return 'text-gray-400';
  
  if (metric.includes('affinity') && !metric.includes('probability')) {
    return getAffinityColor(value);
  }
  if (metric.includes('probability')) {
    return getProbabilityColor(value);
  }
  if (metric.includes('iptm') || metric === 'confidence') {
    return getConfidenceColor(value);
  }
  if (metric.includes('plddt')) {
    return getPLDDTColor(value);
  }
  if (metric === 'complex_ipde') {
    return getIPDEColor(value);
  }
  if (metric === 'ptm') {
    return getConfidenceColor(value);
  }
  
  return 'text-gray-400';
};

// Get sort direction for a metric (for table sorting)
export const getMetricSortDirection = (metric: string): 'asc' | 'desc' => {
  const direction = METRIC_DIRECTIONS[metric as keyof typeof METRIC_DIRECTIONS];
  
  // For UI sorting, we want "better" values at the top
  // So negative-better metrics should sort ascending (most negative first)
  // And positive-better metrics should sort descending (highest first)
  return direction === 'negative' ? 'asc' : 'desc';
};

// Format any metric value with appropriate precision
export const formatMetricValue = (metric: string, value: number | undefined | null): string => {
  if (value === undefined || value === null) return 'N/A';
  
  // Special formatting for specific metrics
  if (metric === 'complex_ipde') {
    return `${value.toFixed(2)} Å`;
  }
  
  if (metric.includes('probability') || metric.includes('iptm') || metric.includes('ptm') || metric === 'confidence') {
    return value.toFixed(3);
  }
  
  if (metric.includes('plddt')) {
    return value.toFixed(1);
  }
  
  if (metric.includes('affinity') && !metric.includes('probability')) {
    return value.toFixed(3);
  }
  
  return value.toFixed(3);
};