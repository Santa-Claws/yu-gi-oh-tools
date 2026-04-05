"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import Image from "next/image";
import Link from "next/link";
import { useIdentifyImage, useIdentifyText } from "@/hooks/useCards";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import type { CardIdentifyResponse } from "@/types/card";

export default function IdentifyPage() {
  const [preview, setPreview] = useState<string | null>(null);
  const [textQuery, setTextQuery] = useState("");
  const [result, setResult] = useState<CardIdentifyResponse | null>(null);

  const imageIdentify = useIdentifyImage();
  const textIdentify = useIdentifyText();

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;
      setPreview(URL.createObjectURL(file));
      imageIdentify.mutate(file, { onSuccess: setResult });
    },
    [imageIdentify],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [] },
    maxFiles: 1,
  });

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <h1 className="text-3xl font-bold">Identify a Card</h1>

      {/* Image upload */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Upload Card Image</h2>
        <div
          {...getRootProps()}
          className={`cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition-colors ${
            isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-blue-400"
          }`}
        >
          <input {...getInputProps()} />
          {preview ? (
            <Image src={preview} alt="Preview" width={200} height={280} className="mx-auto rounded-xl" />
          ) : (
            <div className="text-gray-400">
              <p className="text-4xl">📸</p>
              <p className="mt-2">Drag and drop a card image, or click to select</p>
              <p className="text-sm">Supports JPG, PNG, WebP</p>
            </div>
          )}
        </div>
        {imageIdentify.isPending && (
          <p className="mt-3 text-center text-sm text-gray-500">Identifying...</p>
        )}
      </section>

      {/* Text search */}
      <section>
        <h2 className="mb-3 text-lg font-semibold">Or Search by Name / Text</h2>
        <div className="flex gap-2">
          <Input
            value={textQuery}
            onChange={(e) => setTextQuery(e.target.value)}
            placeholder="Card name or description text..."
            onKeyDown={(e) => {
              if (e.key === "Enter" && textQuery.trim()) {
                textIdentify.mutate({ text: textQuery }, { onSuccess: setResult });
              }
            }}
          />
          <Button
            disabled={!textQuery.trim() || textIdentify.isPending}
            loading={textIdentify.isPending}
            onClick={() => textIdentify.mutate({ text: textQuery }, { onSuccess: setResult })}
          >
            Search
          </Button>
        </div>
      </section>

      {/* Results */}
      {result && (
        <section>
          <div className="mb-4 flex items-center gap-3">
            <h2 className="text-lg font-semibold">Results</h2>
            {result.used_vision_fallback && (
              <Badge>Vision AI used</Badge>
            )}
            {result.ocr_confidence !== null && (
              <Badge>OCR: {Math.round((result.ocr_confidence ?? 0) * 100)}%</Badge>
            )}
          </div>

          {result.candidates.length === 0 ? (
            <p className="text-gray-500">No matches found.</p>
          ) : (
            <div className="space-y-3">
              {result.candidates.map((c, i) => (
                <Link
                  key={c.card.id}
                  href={`/cards/${c.card.id}`}
                  className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md"
                >
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-700">
                    {i + 1}
                  </div>
                  {c.card.prints[0]?.image_url_small && (
                    <Image
                      src={c.card.prints[0].image_url_small}
                      alt={c.card.name_en}
                      width={50}
                      height={70}
                      className="rounded-lg"
                    />
                  )}
                  <div className="flex-1">
                    <p className="font-semibold">{c.card.name_en}</p>
                    <p className="text-sm text-gray-500">{c.match_reason}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-green-600">
                      {Math.round(c.confidence * 100)}%
                    </p>
                    <Badge>{c.match_type}</Badge>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
