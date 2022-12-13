import os
num_cores = 6 #specific to my PC
os.environ["XLA_FLAGS"] = '--xla_force_host_platform_device_count=' + str(num_cores)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import mchmc
from benchmark_targets import *
import german_credit

import jax
import jax.numpy as jnp




def benchmarks():

    # targets
    names = ['Ill-Conditioned', 'Bi-Modal', 'Rosenbrock', "Neal's Funnel", 'German Credit', 'Stochastic Volatility']
    targets = [IllConditionedGaussian(100, 100.0), BiModal(d=50, mu1=0.0, mu2=8.0, sigma1=1.0, sigma2=1.0, f=0.2), Rosenbrock(d=36), Funnel(d=20), german_credit.Target(), StochasticVolatility()]
    d = [tar.d for tar in targets]

    #optimal settings
    file = 'submission/Table generalized_LF_q=0.csv'
    results = pd.read_csv(file)
    eps = np.array(results['eps'])
    L = np.array(results['alpha']) * np.sqrt(d)

    varE = np.empty(len(eps))

    for i in range(len(names)):
        print(names[i])
        target = targets[i]
        burn_in, samples = 1000, 1000
        batch_size, num_batches = 50, 20

        sampler = mchmc.Sampler(target, L[i], eps[i], integrator= 'LF', generalized=True)

        X, W, E = sampler.parallel_sample(6, burn_in + num_batches * batch_size, monitor_energy=True, num_cores= 6)

        var = np.empty((6, num_batches))
        for k in range(num_batches):
            imin, imax= burn_in+ k * batch_size, burn_in + (k+1) * batch_size
            e1 = np.average(E[:, imin:imax], weights=W[:, imin:imax], axis= 1)
            e2 = np.average(np.square(E[:, imin:imax]), weights=W[:, imin:imax], axis= 1)
            var[:, k] = (e2 - np.square(e1)) / target.d

        Var = np.median(var, axis = 1)
        varE[i] = np.median(Var)

        plt.title(names[i])
        for i in range(len(E)):
            plt.plot(np.arange(len(E[0]))[1000:], E[i, 1000:], '.')
        plt.savefig(names[i] + '.png')
        plt.show()

    results['energy variance'] = varE

    results.to_csv('submission/Table generalized_LF_q=0_energy.csv', index = False)



def epsilon_dependence():
    num_target = 5
    name = (['STN', 'STN1000', 'ICG', 'rosenbrock', 'funnel', 'german'])[num_target]
    target = ([StandardNormal(d = 100), StandardNormal(d = 1000), IllConditionedGaussian(100, 100.0), Rosenbrock(d = 36), Funnel(d=20), german_credit.Target()])[num_target]
    epsilon = ([np.logspace(np.log10(1), np.log10(15), 15),
                np.logspace(np.log10(1), np.log10(15), 15) * np.sqrt(10),
                np.logspace(np.log10(0.1), np.log10(5), 15),
                np.logspace(np.log10(0.01), np.log10(1.2), 15) / np.sqrt(3),
                np.logspace(np.log10(0.01), np.log10(3), 15),
                np.logspace(np.log10(0.01), np.log10(1.2), 15)])[num_target]

    num_steps, burn_in = 3000, 2000
    Evar = np.empty((len(epsilon), 3))
    L = 1.0 * jnp.sqrt(target.d) * np.sqrt(np.average(target.variance))
    #L = np.inf
    sampler = mchmc.Sampler(target, L, 1.0, 'LF', True)

    for i in range(len(epsilon)):
        print(i)
        sampler.eps = epsilon[i]
        #bias[i, :] = sampler.sample('prior', num_steps, L, key, generalized= False, integrator= 'LF', ess= True)
        X, W, E = sampler.parallel_sample(10, num_steps, monitor_energy=True)
        E = E[:, burn_in:]
        W = W[:, burn_in:]

        var = np.average(np.square(E - np.average(E, weights= W, axis = 1)[:, None]), weights=W, axis = 1) / target.d
        med = np.median(var)
        lower_quart, upper_quart = np.median(var[var < med]), np.median(var[var > med])
        Evar[i] = [med, lower_quart, upper_quart]

    df = pd.DataFrame({'eps': epsilon, 'varE': Evar[:, 0], 'low err varE': Evar[:, 1], 'high err varE': Evar[:, 2]})
    df.to_csv('Tests/data/energy/'+name+'.csv', index= False)




def dimension_dependence():

    dimensions = [100, 300, 1000, 3000, 10000]
    name = ['kappa1', 'kappa100', 'Rosenbrock']
    targets = [lambda d: StandardNormal(d), lambda d: IllConditionedGaussian(d, 100.0), lambda d: Rosenbrock(d)]
    DF = [pd.read_csv('Tests/data/dimensions_dependence/'+nam+'g.csv') for nam in name]
    L = np.array([np.array(df['alpha']) * np.sqrt(dimensions) for df in DF])
    eps = np.array([np.array(df['eps']) for df in DF])

    num_steps, burn_in = 3000, 2000
    Evar = np.empty((len(targets), len(dimensions), 3))


    for num in range(len(targets)):
        print(name[num])

        for i in range(len(dimensions)):
            sampler = mchmc.Sampler(targets[num](dimensions[i]), L[num, i], eps[num, i], 'LF', True)

            X, w, E = sampler.parallel_sample(10, num_steps, monitor_energy=True)
            E = E[:, burn_in:]
            w = w[:, burn_in:]

            var = np.average(np.square(E - np.average(E, weights=w, axis=1)[:, None]), weights=w, axis=1) / dimensions[i]
            med = np.median(var)
            lower_quart, upper_quart = np.median(var[var < med]), np.median(var[var > med])
            Evar[num, i] = [med, lower_quart, upper_quart]

    np.save('Tests/data/energy/dimension_scaling.npy', Evar)

    #for d in df['d']df['eps']



if __name__ == '__main__':

    benchmarks()
    #dimension_dependence()
    #epsilon_dependence()