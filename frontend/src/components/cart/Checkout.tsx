import React, { useState } from 'react';
import { X, User, Mail, MapPin, CreditCard, ShoppingBag, Loader } from 'lucide-react';
import { useCart } from '../../contexts/CartContext';
import { createOrder } from '../../services/api';

interface CheckoutProps {
  isOpen: boolean;
  onClose: () => void;
}

interface CustomerInfo {
  email: string;
  fullName: string;
  shippingAddress: string;
  billingAddress: string;
  paymentMethod: string;
}

const Checkout: React.FC<CheckoutProps> = ({ isOpen, onClose }) => {
  const { cart, clearCart } = useCart();
  const [customerInfo, setCustomerInfo] = useState<CustomerInfo>({
    email: '',
    fullName: '',
    shippingAddress: '',
    billingAddress: '',
    paymentMethod: 'credit_card'
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(false);
  const [orderError, setOrderError] = useState<string | null>(null);
  const [orderId, setOrderId] = useState<string>('');
  const [useSameAddress, setUseSameAddress] = useState(true);

  if (!isOpen) return null;

  const handleInputChange = (field: keyof CustomerInfo, value: string) => {
    setCustomerInfo(prev => ({ ...prev, [field]: value }));
    if (field === 'shippingAddress' && useSameAddress) {
      setCustomerInfo(prev => ({ ...prev, billingAddress: value }));
    }
  };

  const handleAddressToggle = (checked: boolean) => {
    setUseSameAddress(checked);
    if (checked) {
      setCustomerInfo(prev => ({ ...prev, billingAddress: prev.shippingAddress }));
    }
  };

  const validateForm = (): boolean => {
    const { email, fullName, shippingAddress, billingAddress } = customerInfo;
    return !!(email && fullName && shippingAddress && billingAddress);
  };

  const handleSubmitOrder = async () => {
    if (!validateForm()) {
      setOrderError('Please fill in all required fields');
      return;
    }

    setIsProcessing(true);
    setOrderError(null);

    try {
      // Prepare order items in the format expected by the OrderAgent
      const orderItems = cart.items.map(item => ({
        sku: item.id, // Using product ID as SKU for now
        quantity: item.quantity
      }));

      const orderRequest = {
        customer_email: customerInfo.email,
        customer_name: customerInfo.fullName,
        items: JSON.stringify(orderItems),
        shipping_address: customerInfo.shippingAddress,
        billing_address: customerInfo.billingAddress,
        payment_method: customerInfo.paymentMethod
      };      const response = await createOrder(orderRequest);
      
      console.log('Order response:', response); // Debug log
      console.log('Order response success:', response.success); // Debug log
      console.log('Order response order_id:', response.order_id); // Debug log
        if (response.success) {
        setOrderId(response.order_id || '');
        setOrderSuccess(true);
        clearCart(); // Clear cart on successful order
      } else {
        setOrderError(response.message || 'Failed to create order');
      }
    } catch (error) {
      console.error('Order creation error:', error);
      setOrderError(error instanceof Error ? error.message : 'Failed to create order');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClose = () => {
    if (!isProcessing) {
      setOrderSuccess(false);
      setOrderError(null);
      setCustomerInfo({
        email: '',
        fullName: '',
        shippingAddress: '',
        billingAddress: '',
        paymentMethod: 'credit_card'
      });
      onClose();
    }
  };

  if (orderSuccess) {
    return (
      <>
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <ShoppingBag className="w-8 h-8 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-secondary-800 mb-2">Order Placed Successfully!</h2>
            <p className="text-secondary-600 mb-4">
              Your order has been created and is being processed.
            </p>
            <div className="bg-secondary-50 rounded-xl p-4 mb-6">
              <p className="text-sm text-secondary-600">Order ID</p>
              <p className="font-mono text-primary-600 font-semibold">{orderId}</p>
            </div>
            <button
              onClick={handleClose}
              className="btn-primary w-full"
            >
              Continue Shopping
            </button>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
      
      {/* Checkout Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
        <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-secondary-200 bg-gradient-to-r from-primary-50 to-primary-100 rounded-t-2xl">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-500 rounded-xl">
                <CreditCard className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-secondary-800">Checkout</h2>
                <p className="text-sm text-secondary-600">Complete your purchase</p>
              </div>
            </div>
            <button
              onClick={handleClose}
              disabled={isProcessing}
              className="p-2 hover:bg-secondary-100 rounded-xl transition-colors duration-200 disabled:opacity-50"
            >
              <X className="w-5 h-5 text-secondary-600" />
            </button>
          </div>

          <div className="p-6 space-y-6">
            {/* Order Summary */}
            <div className="bg-secondary-50 rounded-xl p-4">
              <h3 className="font-semibold text-secondary-800 mb-3">Order Summary</h3>
              <div className="space-y-2">
                {cart.items.map((item) => (
                  <div key={item.id} className="flex justify-between text-sm">
                    <span>{item.name} × {item.quantity}</span>
                    <span>${(item.price * item.quantity).toFixed(2)}</span>
                  </div>
                ))}
                <div className="border-t border-secondary-200 pt-2 mt-2">
                  <div className="flex justify-between font-semibold">
                    <span>Total</span>
                    <span className="text-primary-600">${cart.total.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Customer Information */}
            <div className="space-y-4">
              <h3 className="font-semibold text-secondary-800 flex items-center">
                <User className="w-4 h-4 mr-2" />
                Customer Information
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-1">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    value={customerInfo.fullName}
                    onChange={(e) => handleInputChange('fullName', e.target.value)}
                    className="w-full px-3 py-2 border border-secondary-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                    placeholder="John Doe"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-1">
                    Email Address *
                  </label>
                  <input
                    type="email"
                    value={customerInfo.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    className="w-full px-3 py-2 border border-secondary-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                    placeholder="john@example.com"
                  />
                </div>
              </div>
            </div>

            {/* Shipping Address */}
            <div className="space-y-4">
              <h3 className="font-semibold text-secondary-800 flex items-center">
                <MapPin className="w-4 h-4 mr-2" />
                Shipping Address
              </h3>
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">
                  Address *
                </label>
                <textarea
                  value={customerInfo.shippingAddress}
                  onChange={(e) => handleInputChange('shippingAddress', e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-secondary-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors resize-none"
                  placeholder="123 Main St, City, State, ZIP Code"
                />
              </div>
            </div>

            {/* Billing Address */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-secondary-800 flex items-center">
                  <MapPin className="w-4 h-4 mr-2" />
                  Billing Address
                </h3>
                <label className="flex items-center space-x-2 text-sm">
                  <input
                    type="checkbox"
                    checked={useSameAddress}
                    onChange={(e) => handleAddressToggle(e.target.checked)}
                    className="rounded"
                  />
                  <span>Same as shipping</span>
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">
                  Address *
                </label>
                <textarea
                  value={customerInfo.billingAddress}
                  onChange={(e) => handleInputChange('billingAddress', e.target.value)}
                  disabled={useSameAddress}
                  rows={3}
                  className="w-full px-3 py-2 border border-secondary-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors resize-none disabled:bg-secondary-50 disabled:text-secondary-500"
                  placeholder="123 Main St, City, State, ZIP Code"
                />
              </div>
            </div>

            {/* Payment Method */}
            <div className="space-y-4">
              <h3 className="font-semibold text-secondary-800 flex items-center">
                <CreditCard className="w-4 h-4 mr-2" />
                Payment Method
              </h3>
              <div>
                <select
                  value={customerInfo.paymentMethod}
                  onChange={(e) => handleInputChange('paymentMethod', e.target.value)}
                  className="w-full px-3 py-2 border border-secondary-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
                >
                  <option value="credit_card">Credit Card</option>
                  <option value="paypal">PayPal</option>
                  <option value="bank_transfer">Bank Transfer</option>
                </select>
              </div>
            </div>

            {/* Error Message */}
            {orderError && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                <div className="flex items-center">
                  <X className="w-5 h-5 text-red-500 mr-2" />
                  <p className="text-red-700">{orderError}</p>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-3 pt-4 border-t border-secondary-200">
              <button
                onClick={handleClose}
                disabled={isProcessing}
                className="btn-secondary disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitOrder}
                disabled={isProcessing || !validateForm()}
                className="btn-primary disabled:opacity-50 flex items-center justify-center"
              >
                {isProcessing ? (
                  <>
                    <Loader className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  `Place Order - $${cart.total.toFixed(2)}`
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Checkout;
