'use client';

import React, { useState } from 'react';
import { Sparkles, Copy, Check, Loader2, ChevronDown, ChevronUp } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ListingGenerationRequest, ListingGenerationResult } from '@/lib/types';
import { generateListing } from '@/lib/api';

interface ListingGeneratorProps {
  propertyId: string;
  className?: string;
  compact?: boolean;
}

// Platform character limits for display
const PLATFORM_LIMITS: Record<string, number> = {
  facebook: 63206,
  instagram: 2200,
  linkedin: 3000,
  twitter: 280,
};

export function ListingGenerator({
  propertyId,
  className,
  compact = false,
}: ListingGeneratorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ListingGenerationResult | null>(null);

  // Copy state
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const handleGenerate = async () => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    // Use sensible defaults - matches backend ListingGenerationRequest
    const request: ListingGenerationRequest = {
      property_id: propertyId,
      tone: 'professional',
      language: 'en',
      generate_description: true,
      generate_headlines: true,
      headline_count: 5,
      headline_style: 'catchy',
      generate_social: true,
      social_platform: 'facebook',
    };

    try {
      const response = await generateListing(request);
      if (response.error) {
        setError(response.error);
      } else {
        setResult(response);
        setIsOpen(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    }
  };

  const getCharCountColor = (count: number, max: number) => {
    const ratio = count / max;
    if (ratio > 1) return 'text-destructive';
    if (ratio > 0.9) return 'text-warning';
    return 'text-success';
  };

  return (
    <div className={cn('relative', className)}>
      {/* Generate Button */}
      <div className="flex items-center gap-2">
        <Button
          onClick={handleGenerate}
          disabled={isLoading}
          variant="outline"
          size={compact ? 'sm' : 'default'}
          className="gap-2"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Sparkles className="h-4 w-4" aria-hidden="true" />
          )}
          {isLoading ? 'Generating...' : 'Generate Listing'}
        </Button>

        {result && !compact && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsOpen(!isOpen)}
            className="gap-1"
            aria-label={isOpen ? 'Hide results' : 'Show results'}
            aria-expanded={isOpen}
          >
            {isOpen ? (
              <>
                <ChevronUp className="h-4 w-4" aria-hidden="true" />
                Hide
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
                Show Results
              </>
            )}
          </Button>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div
          className="mt-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive bg-destructive/15/20 dark:text-destructive"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* Results Panel */}
      {result && isOpen && (
        <Card className="mt-4">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">Generated Listing Content</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="description" className="w-full">
              <TabsList className="mb-4">
                <TabsTrigger value="description">Description</TabsTrigger>
                <TabsTrigger value="headlines">Headlines</TabsTrigger>
                <TabsTrigger value="social">Social Media</TabsTrigger>
              </TabsList>

              {/* Description Tab */}
              <TabsContent value="description">
                {result.description ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        {result.char_counts.description?.toLocaleString()} chars
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(result.description!, 'description')}
                        className="gap-1"
                      >
                        {copiedField === 'description' ? (
                          <>
                            <Check className="h-3 w-3" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3" />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>
                    <div className="rounded-md bg-muted p-4 text-sm whitespace-pre-wrap">
                      {result.description}
                    </div>
                  </div>
                ) : (
                  <p className="text-muted-foreground text-sm">No description generated</p>
                )}
              </TabsContent>

              {/* Headlines Tab */}
              <TabsContent value="headlines">
                {result.headlines && result.headlines.length > 0 ? (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        {result.headlines.length} headlines generated
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(result.headlines!.join('\n'), 'headlines')}
                        className="gap-1"
                      >
                        {copiedField === 'headlines' ? (
                          <>
                            <Check className="h-3 w-3" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3" />
                            Copy All
                          </>
                        )}
                      </Button>
                    </div>
                    <ul className="space-y-2">
                      {result.headlines.map((headline, index) => (
                        <li
                          key={index}
                          className="flex items-start justify-between gap-2 rounded-md bg-muted p-3"
                        >
                          <span className="text-sm">{headline}</span>
                          <div className="flex items-center gap-2 shrink-0">
                            <span className={cn('text-xs', getCharCountColor(headline.length, 80))}>
                              {headline.length}c
                            </span>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleCopy(headline, `hl-${index}`)}
                              className="h-6 w-6 p-0"
                              aria-label={
                                copiedField === `hl-${index}` ? 'Copied' : 'Copy headline'
                              }
                            >
                              {copiedField === `hl-${index}` ? (
                                <Check className="h-3 w-3" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </Button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="text-muted-foreground text-sm">No headlines generated</p>
                )}
              </TabsContent>

              {/* Social Media Tab */}
              <TabsContent value="social">
                {result.social_content ? (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span
                        className={cn(
                          'text-sm',
                          getCharCountColor(
                            result.char_counts.social || 0,
                            PLATFORM_LIMITS.facebook
                          )
                        )}
                      >
                        {result.char_counts.social?.toLocaleString()} /{' '}
                        {PLATFORM_LIMITS.facebook.toLocaleString()} chars
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(result.social_content!, 'social')}
                        className="gap-1"
                      >
                        {copiedField === 'social' ? (
                          <>
                            <Check className="h-3 w-3" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3" />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>
                    <div className="rounded-md bg-muted p-4 text-sm whitespace-pre-wrap">
                      {result.social_content}
                    </div>
                  </div>
                ) : (
                  <p className="text-muted-foreground text-sm">No social content generated</p>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
