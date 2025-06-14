import { CartProvider } from './contexts/CartContext';
import ChatInterface from './components/chat/ChatInterface';
import ShoppingCart from './components/cart/ShoppingCart';
import CartButton from './components/cart/CartButton';
import BackendStatus from './components/debug/BackendStatus';
import './App.css';

function App() {
  return (
    <CartProvider>
      <div className="App min-h-screen gradient-background">
        {/* Header with Cart Button */}
        <header className="fixed top-0 left-0 right-0 z-30 bg-white/80 backdrop-blur-sm border-b border-secondary-200 shadow-soft">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-primary-500 rounded-xl">
                  <span className="text-white font-bold text-lg">PP</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-secondary-800">Price Pilot</h1>
                  <p className="text-sm text-secondary-600">Your AI Shopping Assistant</p>
                </div>
              </div>
              <CartButton />
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="pt-16">
          <ChatInterface />
        </main>

        {/* Shopping Cart Sidebar */}
        <ShoppingCart />

        {/* Backend Connection Status */}
        <BackendStatus />
      </div>
    </CartProvider>
  );
}

export default App;
