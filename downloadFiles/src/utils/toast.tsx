import { toast, ToastOptions } from 'react-toastify';
import { FaCheckCircle, FaTimesCircle, FaInfoCircle } from 'react-icons/fa';
import './toast.css';

const defaultOptions: ToastOptions = {
    position: "top-center",
    autoClose: 3000,
    hideProgressBar: false,
    closeOnClick: true,
    pauseOnHover: true,
    draggable: true,
    progress: undefined,
    theme: "dark",
    className: 'custom-toast-container',
};

export const notifySuccess = (message: string) => {
    toast.success(message, {
        ...defaultOptions,
        icon: <FaCheckCircle style={{ color: '#22c55e' }} />,
        className: 'custom-toast success',
    });
};

export const notifyError = (message: string) => {
    toast.error(message, {
        ...defaultOptions,
        icon: <FaTimesCircle style={{ color: '#ef4444' }} />,
        className: 'custom-toast error',
    });
};

export const notifyInfo = (message: string) => {
    toast.info(message, {
        ...defaultOptions,
        icon: <FaInfoCircle style={{ color: '#3b82f6' }} />,
        className: 'custom-toast info',
    });
};
