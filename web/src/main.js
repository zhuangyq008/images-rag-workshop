import { createApp } from 'vue';
import App from './App.vue';
import router from './router';


import Aura from '@primevue/themes/aura';
import PrimeVue from 'primevue/config';
import ConfirmationService from 'primevue/confirmationservice';
import ToastService from 'primevue/toastservice';

import '@/assets/styles.scss';
import '@/assets/tailwind.css';

const app = createApp(App);

window.apiUrl = 'https://qp4vxwpqq2.execute-api.us-east-1.amazonaws.com/prod'; // 'https://hot26r2aaa.execute-api.us-east-1.amazonaws.com/prod';

app.use(router);
app.use(PrimeVue, {
    theme: {
        preset: Aura,
        options: {
            darkModeSelector: '.app-dark'
        }
    }
});
app.use(ToastService);
app.use(ConfirmationService);

app.mount('#app');
