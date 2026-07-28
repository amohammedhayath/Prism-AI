import React, { useState } from 'react';
import axios from 'axios';

const ResumeUploader = ({ onUploadSuccess }) => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState('');

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://35.188.159.223';
            const response = await axios.post(`${API_BASE_URL}/api/resumes/upload/`, formData);
            // const response = await axios.post('/api/resumes/upload/', formData);
            setMessage(`✅ Upload Successful! ID: ${response.data.id}`);
            onUploadSuccess(response.data.id);
        } catch (error) {
            setMessage('❌ Upload Failed');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div>
            <div className="d-flex align-items-center mb-4">
                 <div className="bg-primary rounded-circle p-2 me-3 d-flex align-items-center justify-content-center" style={{width: 40, height: 40}}>
                    <span className="text-white fw-bold">1</span>
                </div>
                <h4 className="mb-0">Upload Resume</h4>
            </div>

            <div className="d-flex gap-3">
                <input 
                    type="file" 
                    className="form-control" 
                    onChange={(e) => setFile(e.target.files[0])}
                />
                <button 
                    className="btn btn-primary-glass" 
                    onClick={handleUpload} 
                    disabled={uploading}
                >
                    {uploading ? 'Uploading...' : 'Upload'}
                </button>
            </div>
            {message && <div className="mt-3 text-success fw-bold">{message}</div>}
        </div>
    );
};

export default ResumeUploader;
