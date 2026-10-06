import { useState, useRef } from 'react';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

  const handleFile = (file) => {
    setError(null);
    setResult(null);

    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setError('Please select a valid image file (JPEG, PNG, WebP).');
      return;
    }

    if (file.size > MAX_SIZE) {
      setError(`Image is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum is 10 MB.`);
      return;
    }

    setImage(file);
    setPreview(URL.createObjectURL(file));
  };

  const handleInputChange = (e) => {
    handleFile(e.target.files[0]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => {
    setDragActive(false);
  };

  const handleReset = () => {
    setImage(null);
    setPreview(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handlePredict = async () => {
    if (!image) {
      setError('Please select an image first.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', image);

    try {
      const response = await fetch(`${API_URL}/predict`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || `Server error (${response.status})`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError('Cannot connect to the API. Make sure the backend is running.');
      } else {
        setError(err.message || 'Something went wrong. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <span className="header__badge">EfficientNet B0</span>
        <h1 className="header__title">Food-101 Classifier</h1>
        <p className="header__subtitle">
          Upload a food image and let the model identify it from 101 categories.
        </p>
      </header>

      {/* Main Card */}
      <div className="card">
        {/* Drop Zone */}
        {!preview && (
          <div
            className={`dropzone ${dragActive ? 'dropzone--active' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <span className="dropzone__icon">📷</span>
            <p className="dropzone__text">
              Drag & drop an image here, or <strong>click to browse</strong>
            </p>
            <span className="dropzone__hint">JPEG, PNG, WebP — up to 10 MB</span>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleInputChange}
            />
          </div>
        )}

        {/* Image Preview */}
        {preview && (
          <div className="preview">
            <img src={preview} alt="Selected food" className="preview__img" />
            <button className="preview__remove" onClick={handleReset} title="Remove image">
              ✕
            </button>
          </div>
        )}

        {/* Predict Button */}
        {preview && !result && (
          <button
            className="btn btn--primary"
            onClick={handlePredict}
            disabled={loading}
          >
            {loading ? (
              <span className="spinner">
                <span className="spinner__dot" />
                <span className="spinner__dot" />
                <span className="spinner__dot" />
                Analyzing...
              </span>
            ) : (
              '🔍 Identify Food'
            )}
          </button>
        )}

        {/* Error */}
        {error && (
          <div className="error">
            <span className="error__icon">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="results">
            {/* Top Prediction */}
            <div className="results__main">
              <p className="results__label">Prediction</p>
              <p className="results__class">{result.prediction.class}</p>
              <p className="results__confidence">
                {(result.prediction.confidence * 100).toFixed(1)}% confidence
              </p>
            </div>

            {/* Top 5 */}
            {result.top_predictions && result.top_predictions.length > 1 && (
              <div>
                <p className="top5__title">Top 5 Predictions</p>
                <ul className="top5">
                  {result.top_predictions.map((item, index) => (
                    <li key={index} className="top5__item">
                      <span className="top5__rank">{index + 1}</span>
                      <span className="top5__name">{item.class}</span>
                      <span className="top5__bar-wrapper">
                        <span
                          className="top5__bar"
                          style={{ width: `${Math.max(item.confidence * 100, 2)}%` }}
                        />
                      </span>
                      <span className="top5__pct">
                        {(item.confidence * 100).toFixed(1)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Try Again */}
            <button className="btn btn--ghost" onClick={handleReset}>
              ↺ Try Another Image
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="footer">
        <p>Powered by TensorFlow · EfficientNetB0 · Food-101 Dataset</p>
      </footer>
    </div>
  );
}

export default App;
