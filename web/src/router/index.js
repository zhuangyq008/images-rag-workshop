import AppLayout from '@/layout/AppLayout.vue';
import { createRouter, createWebHistory } from 'vue-router';

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            component: AppLayout,
            children: [
                {
                    path: '/',
                    name: 'ImagesView',
                    component: () => import('@/views/uikit/ListDoc.vue')
                }
                // ,
                // {
                //     path: '/uikit/formlayout',
                //     name: 'formlayout',
                //     component: () => import('@/views/uikit/FormLayout.vue')
                // },
                // {
                //     path: '/uikit/panel',
                //     name: 'panel',
                //     component: () => import('@/views/uikit/PanelsDoc.vue')
                // }
            ]
        },
        {
            path: '/landing',
            name: 'landing',
            component: () => import('@/views/pages/Landing.vue')
        },
        {
            path: '/pages/notfound',
            name: 'notfound',
            component: () => import('@/views/pages/NotFound.vue')
        },

        {
            path: '/auth/login',
            name: 'login',
            component: () => import('@/views/pages/auth/Login.vue')
        },
        {
            path: '/auth/access',
            name: 'accessDenied',
            component: () => import('@/views/pages/auth/Access.vue')
        },
        {
            path: '/auth/error',
            name: 'error',
            component: () => import('@/views/pages/auth/Error.vue')
        }
    ]
});

export default router;
