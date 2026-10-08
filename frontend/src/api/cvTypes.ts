/**
 * Hand-maintained types for the camera-pipeline endpoints (storelab/cv/*, exposed via
 * storelab/main.py cv_demo/cv_upload — both bare `Response`, no OpenAPI schema).
 * Most of the raw CV payload (frames/detections/events/background) isn't rendered —
 * only what the About screen's camera-pipeline demo actually shows is typed precisely.
 */

export interface CvTrackPoint {
  t: number;
  x: number;
  y: number;
  zone: string;
}

export interface CvZoneVisit {
  zone: string;
  t_enter: number;
  t_exit: number;
  x: number;
  y: number;
  dwell_s: number;
}

export interface CvTrack {
  anonymous_track_id: string;
  points: CvTrackPoint[];
  zone_visits: CvZoneVisit[];
  /** Zones visited in order — the shopper's path through the store. */
  journey: string[];
}

export interface CvPreviewFrame {
  frame: number;
  jpeg_base64: string;
}

export interface CvEvaluation {
  people_in_clip: number;
  people_tracked: number;
  recall: number;
  tracks: number;
  fragmented_people: number;
  unmatched_tracks: number;
  mean_position_error_m: number | null;
  note: string;
}

export interface CvCalibration {
  image_points: [number, number][];
  floor_points: [number, number][];
  frame_size: [number, number];
  time_scale: number;
  store_id?: string;
  camera?: string;
  note?: string;
}

export interface CvResult {
  tracks: CvTrack[];
  previews: CvPreviewFrame[];
  /** Only present for the demo clip, scored against its hidden ground truth — never for an uploaded clip. */
  evaluation: CvEvaluation | null;
  calibration: CvCalibration;
  source: string;
}
